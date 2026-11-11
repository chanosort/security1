import sys
# Ensure console output can handle unicode on Windows (cp1252 default)
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
import importlib
import os
import time
import json
import urllib.parse
import urllib.request
import urllib.error

if not hasattr(sys, 'pkgutil_get_loader'):
    def _get_loader(module):
        try:
            return importlib.util.find_spec(module)
        except (AttributeError, ValueError):
            return None
    
    import pkgutil
    pkgutil.get_loader = _get_loader
    print("✓ Applied pkgutil compatibility fix for Python 3.14")

from flask import Flask, request, jsonify, send_from_directory, Response, render_template_string
from flask_cors import CORS
import bcrypt
import jwt
import datetime
from functools import wraps
from config import Config
from db import db

# Get absolute paths to frontend folders
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'FRONTEND')
HTML_DIR = os.path.join(FRONTEND_DIR, 'HTML')
CSS_DIR = os.path.join(FRONTEND_DIR, 'CSS')
JS_DIR = os.path.join(FRONTEND_DIR, 'JS')

print(f"Looking for frontend files in: {FRONTEND_DIR}")
print(f"FRONTEND exists: {os.path.exists(FRONTEND_DIR)}")

if os.path.exists(HTML_DIR):
    print(f"Files in FRONTEND/HTML: {os.listdir(HTML_DIR)}")

# Initialize Flask app
app = Flask(__name__, static_folder=None)
CORS(app, origins=Config.CORS_ORIGINS)
app.config['SECRET_KEY'] = Config.JWT_SECRET

# ==========================================================
# RATE LIMITING CONFIGURATION
# ==========================================================
# ⚠ UNPROTECTED MODE: Rate limiting is DISABLED for Phase 2 demo.
# To enable it (Phase 3), change the value below to 5.
# ==========================================================
MAX_FAILED_ATTEMPTS = 99999  # ⬅ UNPROTECTED: effectively disabled (Phase 2 demo)
LOCKOUT_DURATION_SECONDS = 60

# In-memory storage for failed attempts
# Format: { 'email@example.com': {'count': 5, 'first_attempt': timestamp} }
login_attempts = {}


# ===== CACHE CONTROL FOR STATIC FILES =====
@app.after_request
def add_cache_control(response):
    """Prevent caching of dynamic/API responses and static assets"""
    # Never cache API responses (auth, data) so dashboards stay fresh
    if request.path.startswith('/api/') or request.path.startswith('/stream_test') or request.path.startswith('/lab_test'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif response.headers.get('Content-Type', '').startswith('text/css'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif response.headers.get('Content-Type', '').startswith('application/javascript'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# ===== TEST ROUTE =====
@app.route('/test')
def test():
    return jsonify({'message': 'Test route is working!'})


# ===== SERVE FRONTEND =====
@app.route('/')
def serve_index():
    try:
        return send_from_directory(HTML_DIR, 'index.html')
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404


@app.route('/HTML/<path:filename>')
def serve_html(filename):
    try:
        return send_from_directory(HTML_DIR, filename)
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404


@app.route('/CSS/<path:filename>')
def serve_css(filename):
    try:
        return send_from_directory(CSS_DIR, filename)
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404


@app.route('/JS/<path:filename>')
def serve_js(filename):
    try:
        return send_from_directory(JS_DIR, filename)
    except Exception as e:
        return jsonify({'error': f'File not found: {str(e)}'}), 404


# ===== AUTHENTICATION DECORATOR =====
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['userId']
            request.user_email = data['email']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        
        return f(*args, **kwargs)
    return decorated


# ===== USER ROUTES =====

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True) or {}
        full_name = data.get('full_name')
        email = data.get('email')
        password = data.get('password')
        currency = data.get('currency', 'PHP')
        monthly_budget = data.get('monthly_budget', 0)
        
        if not all([full_name, email, password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Password minimum length check (6 characters)
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        existing = db.execute_query("SELECT * FROM users WHERE email = %s", (email,))
        if existing:
            return jsonify({'error': 'User already exists'}), 400
        
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        result = db.execute_query(
            """INSERT INTO users (full_name, email, currency, monthly_budget, password_hash) 
               VALUES (%s, %s, %s, %s, %s) 
               RETURNING user_id, full_name, email, currency, monthly_budget""",
            (full_name, email, currency, monthly_budget, password_hash.decode('utf-8'))
        )
        
        if not result:
            return jsonify({'error': 'Failed to create user'}), 500
        
        user = dict(result[0])
        token = jwt.encode({
            'userId': user['user_id'],
            'email': user['email'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({'user': user, 'token': token, 'message': 'Registration successful!'}), 201
        
    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """
    ⚠ UNPROTECTED LOGIN ROUTE (Phase 2 Demo)
    - No rate limiting active (MAX_FAILED_ATTEMPTS = 99999)
    - Every attempt goes through bcrypt verification
    - Returns 401 on failure, 200 on success
    """
    try:
        # Accept BOTH JSON and form-urlencoded (for the lab tool)
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()
        
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({'error': 'Missing email or password'}), 400
        
        # =====================================================
        # RATE LIMITING CHECK (disabled in unprotected mode)
        # =====================================================
        now = time.time()
        
        if email in login_attempts:
            record = login_attempts[email]
            
            if now - record['first_attempt'] > LOCKOUT_DURATION_SECONDS:
                login_attempts[email] = {'count': 0, 'first_attempt': now}
            elif record['count'] >= MAX_FAILED_ATTEMPTS:
                remaining = int(LOCKOUT_DURATION_SECONDS - (now - record['first_attempt']))
                return jsonify({
                    'error': f'Too many failed attempts. Account temporarily locked. Try again in {remaining} seconds.'
                }), 429
        # =====================================================
        
        # Real login: verify against bcrypt hash in PostgreSQL
        result = db.execute_query("SELECT * FROM users WHERE email = %s", (email,))
        if not result:
            if email not in login_attempts:
                login_attempts[email] = {'count': 1, 'first_attempt': now}
            else:
                login_attempts[email]['count'] += 1
            return jsonify({'error': 'Invalid credentials'}), 401
        
        user = dict(result[0])
        if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            if email not in login_attempts:
                login_attempts[email] = {'count': 1, 'first_attempt': now}
            else:
                login_attempts[email]['count'] += 1
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # SUCCESS — reset the counter
        if email in login_attempts:
            del login_attempts[email]
        
        del user['password_hash']
        token = jwt.encode({
            'userId': user['user_id'],
            'email': user['email'],
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        
        return jsonify({'user': user, 'token': token, 'message': 'Login successful!'})
        
    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


# ===== OTHER API ROUTES =====
@app.route('/api/categories', methods=['GET'])
@token_required
def get_categories():
    try:
        result = db.execute_query(
            "SELECT * FROM categories WHERE user_id = %s ORDER BY category_name",
            (request.user_id,)
        )
        return jsonify([dict(row) for row in result])
    except Exception as e:
        print(f"Get categories error: {e}")
        return jsonify({'error': 'Failed to fetch categories'}), 500


@app.route('/api/categories', methods=['POST'])
@token_required
def create_category():
    try:
        data = request.get_json(silent=True) or {}
        category_name = data.get('category_name')
        category_type = data.get('category_type')
        
        if not all([category_name, category_type]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        result = db.execute_query(
            """INSERT INTO categories (user_id, category_name, category_type) 
               VALUES (%s, %s, %s) 
               RETURNING *""",
            (request.user_id, category_name, category_type)
        )
        return jsonify(dict(result[0])), 201
    except Exception as e:
        print(f"Create category error: {e}")
        return jsonify({'error': 'Failed to create category'}), 500


@app.route('/api/transactions', methods=['GET'])
@token_required
def get_transactions():
    try:
        result = db.execute_query(
            """SELECT t.*, c.category_name 
               FROM transactions t
               JOIN categories c ON t.category_id = c.category_id
               WHERE t.user_id = %s 
               ORDER BY t.transaction_date DESC""",
            (request.user_id,)
        )
        return jsonify([dict(row) for row in result])
    except Exception as e:
        print(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500


@app.route('/api/transactions', methods=['POST'])
@token_required
def create_transaction():
    try:
        data = request.get_json(silent=True) or {}
        category_id = data.get('category_id')
        transaction_type = data.get('transaction_type')
        amount = data.get('amount')
        description = data.get('description')
        transaction_date = data.get('transaction_date')
        
        result = db.execute_query(
            """INSERT INTO transactions 
               (user_id, category_id, transaction_type, amount, description, transaction_date) 
               VALUES (%s, %s, %s, %s, %s, %s) 
               RETURNING *""",
            (request.user_id, category_id, transaction_type, amount, description, 
             transaction_date or datetime.datetime.now().strftime('%Y-%m-%d'))
        )
        return jsonify(dict(result[0])), 201
    except Exception as e:
        print(f"Create transaction error: {e}")
        return jsonify({'error': 'Failed to create transaction'}), 500


@app.route('/api/budgets', methods=['GET'])
@token_required
def get_budgets():
    try:
        result = db.execute_query(
            """SELECT b.*, c.category_name 
               FROM budgets b
               JOIN categories c ON b.category_id = c.category_id
               WHERE b.user_id = %s 
               ORDER BY b.year DESC, b.month DESC""",
            (request.user_id,)
        )
        return jsonify([dict(row) for row in result])
    except Exception as e:
        print(f"Get budgets error: {e}")
        return jsonify({'error': 'Failed to fetch budgets'}), 500


@app.route('/api/budgets', methods=['POST'])
@token_required
def create_budget():
    try:
        data = request.get_json(silent=True) or {}
        category_id = data.get('category_id')
        amount = data.get('amount')
        month = data.get('month')
        year = data.get('year')
        
        result = db.execute_query(
            """INSERT INTO budgets (user_id, category_id, amount, month, year) 
               VALUES (%s, %s, %s, %s, %s) 
               RETURNING *""",
            (request.user_id, category_id, amount, month, year)
        )
        return jsonify(dict(result[0])), 201
    except Exception as e:
        print(f"Create budget error: {e}")
        return jsonify({'error': 'Failed to create budget'}), 500


# ==========================================================
# LAB TEST ROUTES (Brute Force Tool)
# ==========================================================

# 1. Common Passwords List
common_passwords = [
    "1234", "12345", "123456", "12345678", "password", "password123",
    "admin", "admin123", "admin1234", "qwerty", "welcome", "student", "student123"
]

# 2. Numeric Passwords List (000000 to 005000)
numeric_passwords = [str(i).zfill(6) for i in range(5001)]
password_list = list(dict.fromkeys(common_passwords + numeric_passwords))


def test_login(target_url, login_type, login_value, password):
    """
    Sends a login attempt using JSON (which Flask expects).
    Returns success=True only if the server responds with HTTP 200 or 3xx.
    """
    data = {}
    if login_type == "username":
        data["email"] = login_value
    elif login_type == "email":
        data["email"] = login_value
    else:
        return {"success": False, "http_code": 0, "error": "Invalid login type"}

    data["password"] = password

    encoded_data = json.dumps(data).encode('utf-8')

    req = urllib.request.Request(target_url, data=encoded_data, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('User-Agent', 'Cyber-Lab-Localhost-Tester/1.0')

    try:
        class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        opener = urllib.request.build_opener(NoRedirectHandler)
        response = opener.open(req, timeout=10)
        http_code = response.getcode()

    except urllib.error.HTTPError as e:
        http_code = e.code
    except Exception as e:
        return {"success": False, "http_code": 0, "error": str(e)}

    success = (300 <= http_code < 400) or (http_code == 200)
    return {"success": success, "http_code": http_code, "error": ""}


@app.route('/lab_test')
def lab_test():
    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CYBER LAB // Authentication Tester</title>
    <style>
        * { box-sizing: border-box; }
        html, body { margin: 0; padding: 0; width: 100%; min-height: 100%; font-family: "Courier New", Consolas, monospace; background: #020604; color: #00ff88; }
        body { overflow-x: hidden; background: radial-gradient(circle at 50% 0%, rgba(0,255,120,0.08), transparent 40%), radial-gradient(circle at 0% 100%, rgba(0,180,255,0.06), transparent 35%), #020604; }
        body::before { content: ""; position: fixed; inset: 0; pointer-events: none; opacity: 0.08; background-image: linear-gradient(rgba(0,255,120,0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(0,255,120,0.15) 1px, transparent 1px); background-size: 40px 40px; animation: gridMove 12s linear infinite; }
        @keyframes gridMove { from { background-position: 0 0, 0 0; } to { background-position: 0 40px, 40px 0; } }
        .wrapper { position: relative; z-index: 1; width: min(1400px, 94%); margin: 30px auto 50px; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 18px 22px; border: 1px solid rgba(0,255,120,0.35); background: rgba(0,10,6,0.88); box-shadow: 0 0 30px rgba(0,255,120,0.08); border-radius: 8px 8px 0 0; }
        .logo { display: flex; align-items: center; gap: 14px; }
        .logo-icon { width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; border: 1px solid #00ff88; color: #00ff88; font-size: 20px; box-shadow: 0 0 15px rgba(0,255,120,0.4); }
        .logo-title { font-size: 18px; font-weight: bold; letter-spacing: 2px; color: #00ff88; }
        .logo-sub { color: #4f9f78; font-size: 11px; margin-top: 3px; letter-spacing: 1px; }
        .local-status { display: flex; align-items: center; gap: 9px; padding: 8px 13px; border: 1px solid rgba(0,255,120,0.35); color: #00ff88; font-size: 11px; letter-spacing: 1px; background: rgba(0,255,120,0.04); }
        .status-dot { width: 9px; height: 9px; border-radius: 50%; background: #00ff88; box-shadow: 0 0 12px #00ff88; animation: pulse 1.4s infinite; }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
        .content { display: grid; grid-template-columns: 380px 1fr; gap: 18px; margin-top: 18px; }
        @media(max-width:900px) { .content { grid-template-columns: 1fr; } }
        .panel { border: 1px solid rgba(0,255,120,0.25); background: rgba(1,12,8,0.90); box-shadow: 0 0 25px rgba(0,255,120,0.04); border-radius: 6px; overflow: hidden; }
        .panel-header { display: flex; justify-content: space-between; padding: 12px 15px; border-bottom: 1px solid rgba(0,255,120,0.18); background: rgba(0,255,120,0.035); font-size: 11px; letter-spacing: 1.5px; }
        .panel-header span:first-child { color: #00ff88; }
        .panel-header span:last-child { color: #276b4c; }
        .config { padding: 18px; }
        .field { margin-bottom: 17px; }
        .field label { display: block; margin-bottom: 7px; color: #52b88a; font-size: 10px; letter-spacing: 1px; }
        input, select { width: 100%; padding: 12px 13px; border: 1px solid rgba(0,255,120,0.25); outline: none; background: #020805; color: #00ff88; font-family: inherit; font-size: 12px; border-radius: 3px; transition: .2s; }
        input:focus, select:focus { border-color: #00ff88; box-shadow: 0 0 12px rgba(0,255,120,0.18); }
        select option { background: #020805; color: #00ff88; }
        .buttons { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
        button { padding: 13px; border: 1px solid #00ff88; background: rgba(0,255,120,0.07); color: #00ff88; font-family: inherit; font-weight: bold; font-size: 11px; letter-spacing: 1px; cursor: pointer; border-radius: 3px; transition: .2s; }
        button:hover { background: rgba(0,255,120,0.18); box-shadow: 0 0 18px rgba(0,255,120,0.25); }
        #stopBtn { border-color: #ff3355; color: #ff3355; background: rgba(255,30,70,0.05); }
        #stopBtn:hover { background: rgba(255,30,70,0.12); box-shadow: 0 0 18px rgba(255,30,70,0.2); }
        .stats { display: grid; grid-template-columns: repeat(4,1fr); gap: 10px; padding: 15px; }
        .stat { border: 1px solid rgba(0,255,120,0.16); background: rgba(0,0,0,0.25); padding: 13px; text-align: center; }
        .stat-label { color: #347858; font-size: 9px; letter-spacing: 1px; margin-bottom: 7px; }
        .stat-value { color: #00ff88; font-size: 18px; font-weight: bold; }
        .terminal-panel { min-height: 650px; }
        .terminal { margin: 0; height: 560px; overflow-y: auto; padding: 18px; background: #010302; color: #00ff88; font-size: 12px; line-height: 1.7; white-space: pre-wrap; text-shadow: 0 0 5px rgba(0,255,120,0.45); scrollbar-width: thin; scrollbar-color: #0c603b #010302; }
        .terminal::before { content: "root@localhost:~$ "; color: #00bfff; }
        .falling-code { position: fixed; top: 0; bottom: 0; width: 170px; overflow: hidden; pointer-events: none; z-index: 0; opacity: 0.42; font-family: "Courier New", Consolas, monospace; color: #00ff88; text-shadow: 0 0 7px rgba(0,255,120,0.55); }
        .falling-code.left { left: 0; }
        .falling-code.right { right: 0; }
        .falling-column { position: absolute; top: -220px; white-space: pre; font-size: 12px; line-height: 1.55; animation: codeFall linear infinite; }
        @keyframes codeFall { from { transform: translateY(-260px); } to { transform: translateY(calc(100vh + 300px)); } }
        @media(max-width:1100px) { .falling-code { width: 95px; opacity: 0.25; } }
        @media(max-width:900px) { .falling-code { display: none; } }
        .terminal .failed-line { color: #ff4d6d !important; font-weight: 700; text-shadow: 0 0 6px rgba(255, 77, 109, 0.45); }
        .terminal .locked-line { color: #ffaa00 !important; font-weight: 700; text-shadow: 0 0 6px rgba(255, 170, 0, 0.5); }
        .terminal .success-line { color: #00ffff !important; font-weight: 800; text-shadow: 0 0 8px rgba(0, 255, 255, 0.65); }
        .terminal .attempt-line { font-weight: 700; }
        .terminal-bar { display: flex; align-items: center; gap: 7px; padding: 9px 12px; border-bottom: 1px solid rgba(0,255,120,0.15); background: #050807; }
        .terminal-circle { width: 9px; height: 9px; border-radius: 50%; background: #244c37; }
        .terminal-title { margin-left: 8px; color: #3d805f; font-size: 10px; }
        .footer { margin-top: 18px; padding: 14px; text-align: center; border: 1px solid rgba(0,255,120,0.15); color: #286044; font-size: 10px; letter-spacing: 1px; background: rgba(0,10,6,0.7); }
        .warning { margin: 0 18px 18px; padding: 11px; border: 1px solid rgba(255,190,0,0.3); background: rgba(255,180,0,0.04); color: #c9a84b; font-size: 10px; line-height: 1.6; }
    </style>
    </head>
    <body>
    <div class="falling-code left" id="fallingLeft"></div>
    <div class="falling-code right" id="fallingRight"></div>
    <div class="wrapper">
        <div class="header">
            <div class="logo">
                <div class="logo-icon">&gt;_</div>
                <div>
                    <div class="logo-title">CYBER LAB</div>
                    <div class="logo-sub">AUTHENTICATION SECURITY TESTER</div>
                </div>
            </div>
            <div class="local-status">
                <span class="status-dot"></span>
                LOCALHOST ONLY
            </div>
        </div>
        <div class="content">
            <div>
                <div class="panel">
                    <div class="panel-header">
                        <span>TARGET CONFIGURATION</span>
                        <span>[CONFIG]</span>
                    </div>
                    <div class="config">
                        <div class="field">
                            <label>TARGET LOGIN URL</label>
                            <input type="text" id="target" value="http://localhost:5000/api/login">
                        </div>
                        <div class="field">
                            <label>LOGIN IDENTIFIER</label>
                            <select id="loginType">
                                <option value="email" selected>EMAIL</option>
                                <option value="username">USERNAME</option>
                            </select>
                        </div>
                        <div class="field">
                            <label>LOGIN VALUE</label>
                            <input type="text" id="loginValue" value="">
                            <div style="color:#4f9f78; font-size:9px; margin-top:5px;">
                                ← Enter the email of the account to test
                            </div>
                        </div>
                        <div class="warning">
                            ⚠ AUTHORIZED LAB USE ONLY<br>
                            This tester is restricted to localhost environments.
                        </div>
                        <div class="buttons">
                            <button id="startBtn">▶ START TEST</button>
                            <button id="stopBtn">■ STOP</button>
                        </div>
                    </div>
                </div>
                <div class="panel" style="margin-top:18px;">
                    <div class="panel-header">
                        <span>SYSTEM STATUS</span>
                        <span>[ONLINE]</span>
                    </div>
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-label">CANDIDATES</div>
                            <div class="stat-value">5013</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">ATTEMPTS</div>
                            <div class="stat-value" id="attemptStat">0</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">FAILED</div>
                            <div class="stat-value" id="failedStat">0</div>
                        </div>
                        <div class="stat">
                            <div class="stat-label">STATUS</div>
                            <div class="stat-value" id="statusStat">IDLE</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="panel terminal-panel">
                <div class="terminal-bar">
                    <span class="terminal-circle"></span>
                    <span class="terminal-circle"></span>
                    <span class="terminal-circle"></span>
                    <span class="terminal-title">CYBER-LAB TERMINAL // localhost</span>
                </div>
                <div class="terminal" id="output">
╔════════════════════════════════════════════╗
║        CYBER AUTHENTICATION LAB            ║
║        LOCALHOST TESTING TERMINAL          ║
╚════════════════════════════════════════════╝

root@localhost:~$ system-check

[+] Environment : LOCALHOST
[+] Security    : LOCAL TARGET ONLY
[+] Status      : READY

root@localhost:~$ waiting for test...
                </div>
            </div>
        </div>
        <div class="footer">
            CYBERSECURITY LABORATORY // AUTHENTICATION SECURITY ANALYSIS // LOCAL ENVIRONMENT
        </div>
    </div>
    <script>
    let running = false;
    let controller = null;
    document.getElementById("startBtn").addEventListener("click", async function () {
        if (running) return;
        running = true;
        const output = document.getElementById("output");
        const status = document.getElementById("statusStat");
        const attempts = document.getElementById("attemptStat");
        const failedStat = document.getElementById("failedStat");
        const loginValue = document.getElementById("loginValue").value;
        if (!loginValue || loginValue.trim() === "") {
            output.textContent = "root@localhost:~$ ./auth-test\\n\\n";
            output.textContent += "[ERROR] Please enter a Login Value (email) first.\\n";
            status.textContent = "ERROR";
            status.style.color = "#ff3355";
            running = false;
            return;
        }
        output.textContent = "root@localhost:~$ ./auth-test\\n\\n";
        attempts.textContent = "0";
        if (failedStat) failedStat.textContent = "0";
        status.textContent = "RUNNING";
        status.style.color = "#00bfff";
        const target = document.getElementById("target").value;
        const loginType = document.getElementById("loginType").value;
        output.textContent += "[*] Initializing test...\\n";
        output.textContent += "[*] Target      : " + target + "\\n";
        output.textContent += "[*] Identifier  : " + loginType + "\\n";
        output.textContent += "[*] Login Value : " + loginValue + "\\n";
        output.textContent += "[*] Environment : LOCALHOST\\n";
        output.textContent += "---------------------------------------------\\n";
        output.scrollTop = output.scrollHeight;
        try {
            controller = new AbortController();
            const params = new URLSearchParams({
                start: '1',
                target: target,
                loginType: loginType,
                loginValue: loginValue
            });
            const response = await fetch("/stream_test?" + params.toString(), {
                method: "GET",
                cache: "no-store",
                signal: controller.signal
            });
            if (!response.ok) throw new Error("HTTP " + response.status);
            if (!response.body) throw new Error("Streaming response is not available.");
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            while (true) {
                const result = await reader.read();
                if (result.done) break;
                const chunk = decoder.decode(result.value, { stream: true });
                if (!chunk) continue;
                const lines = chunk.split("\\n");
                lines.forEach(function (lineText, index) {
                    if (index === lines.length - 1 && lineText === "") return;
                    const line = document.createElement("div");
                    line.textContent = lineText;
                    if (lineText.indexOf(">>> SUCCESS <<<") !== -1) line.className = "success-line";
                    else if (lineText.indexOf("LOCKED OUT") !== -1) line.className = "locked-line";
                    else if (lineText.indexOf("FAILED") !== -1) line.className = "failed-line";
                    else if (lineText.match(/^\\[\\d+\\]/)) line.className = "attempt-line";
                    output.appendChild(line);
                });
                const attemptMatches = chunk.match(/\\[(\\d+)\\]/g);
                if (attemptMatches && attemptMatches.length) {
                    const last = attemptMatches[attemptMatches.length - 1];
                    const number = last.replace(/\\D/g, "");
                    attempts.textContent = parseInt(number, 10);
                }
                if (failedStat) {
                    const failedMatches = chunk.match(/FAILED/g);
                    if (failedMatches) {
                        failedStat.textContent = parseInt(failedStat.textContent || "0", 10) + failedMatches.length;
                    }
                }
                if (chunk.indexOf("SUCCESS") !== -1) {
                    status.textContent = "SUCCESS";
                    status.style.color = "#00ff88";
                }
                if (chunk.indexOf("LOCKED") !== -1) {
                    status.textContent = "LOCKED";
                    status.style.color = "#ffaa00";
                }
                output.scrollTop = output.scrollHeight;
                requestAnimationFrame(function () {
                    output.scrollTo({ top: output.scrollHeight, left: 0, behavior: "auto" });
                });
            }
        } catch (error) {
            if (error.name === "AbortError") {
                output.textContent += "\\n\\n[!] PROCESS STOPPED BY USER.\\n";
                status.textContent = "STOPPED";
                status.style.color = "#ff3355";
            } else {
                output.textContent += "\\n\\n[ERROR] " + error.message + "\\n";
                status.textContent = "ERROR";
                status.style.color = "#ff3355";
            }
            output.scrollTop = output.scrollHeight;
        }
        running = false;
        controller = null;
        if (status.textContent === "RUNNING") {
            status.textContent = "DONE";
            status.style.color = "#00ff88";
        }
    });
    document.getElementById("stopBtn").addEventListener("click", function () {
        if (controller && running) controller.abort();
        running = false;
    });
    setInterval(function () {
        if (running) {
            const output = document.getElementById("output");
            if (output) output.scrollTop = output.scrollHeight;
        }
    }, 100);
    (function () {
        const characters = "01ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz<>[]{}#$%&@";
        function randomCode(length) {
            let result = "";
            for (let i = 0; i < length; i++) {
                result += characters.charAt(Math.floor(Math.random() * characters.length));
                if (i % 3 === 2) result += "\\n";
            }
            return result;
        }
        function createColumns(containerId, count) {
            const container = document.getElementById(containerId);
            if (!container) return;
            for (let i = 0; i < count; i++) {
                const column = document.createElement("div");
                column.className = "falling-column";
                column.textContent = randomCode(95 + Math.floor(Math.random() * 55));
                column.style.left = (5 + Math.random() * 88) + "%";
                column.style.animationDuration = (7 + Math.random() * 10) + "s";
                column.style.animationDelay = (-Math.random() * 12) + "s";
                column.style.opacity = (0.25 + Math.random() * 0.65).toFixed(2);
                column.style.fontSize = (9 + Math.random() * 5) + "px";
                container.appendChild(column);
            }
        }
        createColumns("fallingLeft", 7);
        createColumns("fallingRight", 7);
    })();
    </script>
    </body>
    </html>
    '''
    return render_template_string(html_template)


@app.route('/stream_test')
def stream_test():
    """
    Streams the brute-force results.
    When test_login returns success=True, we BREAK the loop immediately.
    """
    if 'start' not in request.args:
        return "Missing start parameter", 400

    target = request.args.get('target', 'http://localhost:5000/api/login')
    login_type = request.args.get('loginType', 'email')
    login_value = request.args.get('loginValue', '')

    if not login_value:
        return "Missing loginValue parameter. Please enter an email in the lab UI.", 400

    def generate():
        start_time = time.time()
        attempt = 0

        yield "╔════════════════════════════════════════════╗\n"
        yield "║        CYBER AUTHENTICATION LAB            ║\n"
        yield "║        LOCALHOST TESTING TERMINAL          ║\n"
        yield "╚════════════════════════════════════════════╝\n\n"
        yield "[+] Initializing laboratory test...\n"
        yield f"[+] Target      : {target}\n"
        yield f"[+] Identifier  : {login_type}\n"
        yield f"[+] Login Value : {login_value}\n"
        yield f"[+] Candidates  : {len(password_list)}\n"
        yield "[+] Environment : LOCALHOST\n\n"
        yield "──────────────────────────────────────────────\n\n"

        for password in password_list:
            attempt += 1
            result = test_login(target, login_type, login_value, password)
            http_code = result["http_code"]

            if result.get("error"):
                yield f"[ERROR] {result['error']}\n"
                break

            # SUCCESS: Print result and STOP
            if result["success"]:
                yield f"[{attempt:04d}] {password:<18} [HTTP {http_code}]  >>> SUCCESS <<<\n\n"
                elapsed = time.time() - start_time
                yield "╔════════════════════════════════════════════╗\n"
                yield "║              AUTHENTICATION                ║\n"
                yield "║                 MATCH                      ║\n"
                yield "╚════════════════════════════════════════════╝\n\n"
                yield f"[+] Login Identifier : {login_value}\n"
                yield f"[+] Candidate        : {password}\n"
                yield f"[+] HTTP Status      : {http_code}\n"
                yield f"[+] Attempts         : {attempt}\n"
                yield f"[+] Elapsed Time     : {elapsed:.2f} seconds\n\n"
                yield "[+] TEST COMPLETE.\n"
                break

            # LOCKED OUT: HTTP 429
            if http_code == 429:
                yield f"[{attempt:04d}] {password:<18} [HTTP 429]  LOCKED OUT\n"

                if attempt >= 25:
                    yield "\n"
                    yield "──────────────────────────────────────────────\n"
                    yield "[!] RATE LIMIT ACTIVE\n"
                    yield "[!] The account has been locked out.\n"
                    yield "[!] Automated requests are being blocked.\n\n"
                    yield f"[+] Attempts : {attempt}\n"
                    yield f"[+] Time     : {(time.time() - start_time):.2f} seconds\n"
                    yield "──────────────────────────────────────────────\n"
                    break
                continue

            # Regular failure
            yield f"[{attempt:04d}] {password:<18} [HTTP {http_code}]  FAILED\n"
            time.sleep(0.05)

        else:
            elapsed = time.time() - start_time
            yield "\n"
            yield "──────────────────────────────────────────────\n"
            yield "[!] TEST FINISHED\n"
            yield "[!] No configured candidate was detected\n"
            yield "[!] as a successful authentication.\n\n"
            yield f"[+] Attempts : {attempt}\n"
            yield f"[+] Time     : {elapsed:.2f} seconds\n"
            yield "──────────────────────────────────────────────\n"

    return Response(generate(), mimetype='text/plain')


# ===== ERROR HANDLERS =====
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# ===== RUN APPLICATION =====
if __name__ == '__main__':
    print("=" * 60)
    print("Starting Finance Tracker API...")
    print("=" * 60)
    print(f"Frontend folder: {FRONTEND_DIR}")
    print(f"Frontend exists: {os.path.exists(FRONTEND_DIR)}")
    if os.path.exists(HTML_DIR):
        print(f"Files in FRONTEND/HTML: {os.listdir(HTML_DIR)}")
    print("API available at: http://localhost:5000/api/")
    print("Test route: http://localhost:5000/test")
    print("Lab test: http://localhost:5000/lab_test")
    print("=" * 60)
    print(f"⚠ MODE: UNPROTECTED (Phase 2 Demo)")
    print(f"Rate limit: {MAX_FAILED_ATTEMPTS} attempts (effectively disabled)")
    print("=" * 60)
    
    try:
        db.connect()
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
    finally:
        db.close()