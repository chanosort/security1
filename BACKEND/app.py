import sys
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
import re
import html
import secrets
import smtplib
import logging
import urllib.parse
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
load_dotenv(override=True)

if not hasattr(sys, 'pkgutil_get_loader'):
    def _get_loader(module):
        try:
            return importlib.util.find_spec(module)
        except (AttributeError, ValueError):
            return None
    import pkgutil
    pkgutil.get_loader = _get_loader
    print("Applied pkgutil compatibility fix for Python 3.14")

from flask import (Flask, request, jsonify, send_from_directory, Response,
                   render_template_string, session, redirect, abort)
from flask_cors import CORS
import bcrypt
import jwt
import datetime
from functools import wraps

try:
    from flask_wtf.csrf import CSRFProtect, generate_csrf, CSRFError
    CSRF_AVAILABLE = True
except ImportError:
    CSRF_AVAILABLE = False
    print("Flask-WTF not installed - CSRF disabled")

try:
    from cryptography.fernet import Fernet, InvalidToken
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("cryptography not installed - encryption disabled")

from config import Config
from db import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG_PATH = os.path.join(os.path.dirname(BASE_DIR), 'error.log')
logging.basicConfig(
    filename=ERROR_LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
log = logging.getLogger('app')


def _fernet():
    if not CRYPTO_AVAILABLE or not Config.ENCRYPTION_KEY:
        return None
    try:
        return Fernet(Config.ENCRYPTION_KEY.encode())
    except Exception as e:
        log.error(f"Fernet init failed: {e}")
        return None


def encrypt_field(value):
    if value is None:
        return None
    f = _fernet()
    if not f:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_field(value):
    if value is None:
        return None
    f = _fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value


FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), 'FRONTEND')
HTML_DIR = os.path.join(FRONTEND_DIR, 'HTML')
CSS_DIR  = os.path.join(FRONTEND_DIR, 'CSS')
JS_DIR   = os.path.join(FRONTEND_DIR, 'JS')

print(f"Looking for frontend files in: {FRONTEND_DIR}")
print(f"FRONTEND exists: {os.path.exists(FRONTEND_DIR)}")
if os.path.exists(HTML_DIR):
    print(f"Files in FRONTEND/HTML: {os.listdir(HTML_DIR)}")

app = Flask(__name__, static_folder=None)
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

app.config['SECRET_KEY'] = Config.FLASK_SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE']   = False
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(minutes=Config.IDLE_TIMEOUT_MINUTES)
app.config['WTF_CSRF_TIME_LIMIT'] = None

if CSRF_AVAILABLE:
    csrf = CSRFProtect(app)


@app.after_request
def security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    if request.path.startswith('/api/') or request.path.startswith('/stream_test') or request.path.startswith('/lab_test'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    elif response.headers.get('Content-Type', '').startswith('text/css'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    elif response.headers.get('Content-Type', '').startswith('application/javascript'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    return response


def client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()


def log_event(event_type, username_type=None, user_id=None, details=None):
    try:
        db.execute_query(
            """INSERT INTO activity_log
               (event_type, username_type, user_id, ip_address, user_agent, details)
               VALUES (%s,%s,%s,%s,%s,%s)""",
            (event_type, username_type, user_id,
             client_ip(), request.headers.get('User-Agent','')[:500], details)
        )
    except Exception as e:
        log.error(f"log_event failed: {e}")


def send_email(to_addr, subject, body_text, html_body=None):
    load_dotenv(override=True)
    smtp_user = os.getenv('SMTP_USER', '').strip()
    smtp_pw = os.getenv('SMTP_PASSWORD', '').replace(' ', '').strip()
    if not smtp_user or not smtp_pw or 'your_' in smtp_user.lower() or smtp_user == 'your_email@gmail.com':
        log.warning(f"[DEV] SMTP not configured - would send to {to_addr}: {subject}")
        print(f"\n========================================\n[DEV OTP EMAIL SIMULATION]\nTo: {to_addr}\nSubject: {subject}\n{body_text}\n========================================\n")
        return False, "Gmail SMTP is not configured in .env. Please add your Gmail address and 16-character App Password to .env so emails can be sent to Gmail."
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"ExpenseTracker Security <{smtp_user}>"
        msg['To']   = to_addr
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
        if html_body:
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        port = int(os.getenv('SMTP_PORT', '587'))

        if port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=15) as s:
                s.login(smtp_user, smtp_pw)
                s.sendmail(smtp_user, [to_addr], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.starttls()
                s.login(smtp_user, smtp_pw)
                s.sendmail(smtp_user, [to_addr], msg.as_string())
        log.info(f"Email sent successfully to {to_addr}")
        print(f"[SUCCESS] Email sent successfully to {to_addr}")
        return True, None
    except smtplib.SMTPAuthenticationError as e:
        err = f"Gmail authentication failed. Please verify your Gmail address and 16-character App Password in .env: {e}"
        log.error(f"send_email auth error: {e}")
        print(f"[ERROR] {err}")
        return False, err
    except Exception as e:
        err = f"Failed to send email to {to_addr}: {e}"
        log.error(f"send_email failed: {e}")
        print(f"[ERROR] {err}")
        return False, err


def send_otp_email(to_addr, code, purpose):
    labels = {
        'register': 'Registration Verification',
        'login':    'Login Verification',
        'reset':    'Password Reset Verification',
    }
    action_label = labels.get(purpose, 'Security Verification')
    subject = f"ExpenseTracker {action_label}"
    exp_mins = Config.OTP_EXPIRY_MINUTES
    exp_text = "1 minute" if exp_mins == 1 else f"{exp_mins} minutes"

    body = (
        f"ExpenseTracker {action_label}\n\n"
        f"Your verification code is: {code}\n\n"
        f"This code expires in {exp_text}.\n\n"
        "If you did not request this code, ignore this email.\n"
    )

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 500px; margin: auto; padding: 30px; border-radius: 8px; background: #ffffff; color: #202124; border: 1px solid #dadce0;">
        <h2 style="font-size: 20px; font-weight: 600; color: #202124; margin-top: 0; margin-bottom: 20px;">ExpenseTracker {action_label}</h2>
        <p style="font-size: 14px; color: #3c4043; margin-bottom: 15px;">Your verification code is:</p>
        <div style="display: inline-block; font-size: 28px; font-weight: 700; letter-spacing: 5px; color: #ffffff; background: #1a73e8; padding: 10px 22px; border-radius: 6px; margin: 10px 0 20px;">
            {code}
        </div>
        <p style="font-size: 14px; color: #3c4043; margin: 15px 0 10px;">This code expires in {exp_text}.</p>
        <p style="font-size: 14px; color: #5f6368; margin: 0;">If you did not request this code, ignore this email.</p>
    </div>
    """

    print(f"==> [OTP CODE] {action_label.upper()} for {to_addr}: {code} <==")
    return send_email(to_addr, subject, body, html)


def send_alert_email(to_addr, event_type, username, ip, ua, attempts=1):
    subject_map = {
        'LOCKOUT_TIER_1': 'Failed sign-in attempts on your account',
        'LOCKOUT_TIER_2': 'More failed sign-in attempts on your account',
        'LOCKOUT_TIER_3': 'Account locked - too many failed sign-ins',
        'PASSWORD_CHANGED': 'Your password was changed',
    }
    subject = subject_map.get(event_type, 'Security alert')
    now_ph = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    body = (
        f"{subject}\n\n"
        f"Account: {username}\n"
        f"Time (PHT): {now_ph.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"IP address: {ip}\n"
        f"Browser: {ua[:200]}\n"
        f"Failed attempts: {attempts}\n\n"
        "If this was not you, reset your password now using Forgot Password.\n"
    )
    ok = send_email(to_addr, subject, body)
    if ok:
        log_event('ALERT_EMAIL_SENT', 'email', None, f"{event_type} -> {to_addr}")
    return ok


NAME_RE = re.compile(r"^[A-Z][a-z']*(?: [A-Z][a-z']*)*$")
ID_RE   = re.compile(r"^\d{4}-\d{4}$")
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def validate_name(v, field):
    if not v or not v.strip():
        return f"{field} is required."
    v = v.strip()
    if len(v) < 2 or len(v) > Config.MAX_NAME_FIELD:
        return f"{field} must be 2-{Config.MAX_NAME_FIELD} characters."
    if re.search(r"\d", v):
        return f"Numbers are not allowed in {field}."
    if re.search(r"[^A-Za-z ']", v):
        return f"Special characters are not allowed in {field}."
    if "  " in v:
        return "Double space is not allowed."
    if v.isupper() and len(v) > 1:
        return "Do not use all capital letters."
    if re.search(r"(.)\1\1", v, re.I):
        return "Three consecutive identical letters are not allowed."
    if not NAME_RE.match(v):
        return f"First letter of {field} must be capital."
    return None


def validate_username(u):
    if not u:
        return "Username is required."
    if not re.match(r"^[A-Za-z][A-Za-z0-9]*$", u):
        return "Username must start with a letter and contain only letters and digits."
    if len(u) < Config.MIN_USERNAME or len(u) > Config.MAX_USERNAME:
        return f"Username must be {Config.MIN_USERNAME}-{Config.MAX_USERNAME} characters."
    return None


def validate_password(p):
    if not p:
        return "Password is required."
    if len(p) < Config.MIN_PASSWORD:
        return f"Password must be at least {Config.MIN_PASSWORD} characters."
    if len(p) > Config.MAX_PASSWORD:
        return f"Password must be at most {Config.MAX_PASSWORD} characters."
    return None


def compute_age(birthdate_str):
    try:
        bd = datetime.datetime.strptime(birthdate_str, '%Y-%m-%d').date()
    except Exception:
        return None
    today = datetime.date.today()
    if bd > today:
        return None
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))


def hash_answer(answer):
    return bcrypt.hashpw(answer.strip().lower().encode(), bcrypt.gensalt()).decode()


def check_answer(answer, hashed):
    try:
        return bcrypt.checkpw(answer.strip().lower().encode(), hashed.encode())
    except Exception:
        return False


def create_otp(user_id, purpose):
    db.execute_query(
        "UPDATE otps SET consumed=TRUE WHERE user_id=%s AND purpose=%s AND consumed=FALSE",
        (user_id, purpose)
    )
    code = f"{secrets.randbelow(1_000_000):06d}"
    expires = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
    db.execute_query(
        "INSERT INTO otps (user_id, purpose, code_hash, expires_at) VALUES (%s,%s,%s,%s)",
        (user_id, purpose, bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode(), expires)
    )
    return code, expires


def verify_otp(user_id, purpose, code):
    rows = db.execute_query(
        "SELECT * FROM otps WHERE user_id=%s AND purpose=%s AND consumed=FALSE "
        "ORDER BY created_at DESC LIMIT 1",
        (user_id, purpose)
    )
    if not rows:
        return False, 'no_otp'
    row = dict(rows[0])
    exp = row['expires_at']
    now = datetime.datetime.now(datetime.timezone.utc)
    if exp.tzinfo is None:
        now = now.replace(tzinfo=None)
    if now > exp:
        db.execute_query("UPDATE otps SET consumed=TRUE WHERE otp_id=%s", (row['otp_id'],))
        return False, 'expired'
    if row['attempts'] >= 3:
        db.execute_query("UPDATE otps SET consumed=TRUE WHERE otp_id=%s", (row['otp_id'],))
        return False, 'locked'
    if not bcrypt.checkpw(code.encode(), row['code_hash'].encode()):
        db.execute_query("UPDATE otps SET attempts=attempts+1 WHERE otp_id=%s", (row['otp_id'],))
        log_event('OTP_FAILED', 'user_id', user_id, f"purpose={purpose}")
        return False, 'wrong'
    db.execute_query("UPDATE otps SET consumed=TRUE WHERE otp_id=%s", (row['otp_id'],))
    return True, 'ok'


login_attempts = {}
MAX_FAILED_ATTEMPTS   = 3
LOCKOUT_DURATION_SECONDS = Config.LOCKOUT_TIER1_SECONDS
FORGOT_LINK_AFTER     = Config.FAILED_BEFORE_FORGOT

ip_failures = {}


def is_ip_blocked(ip):
    rec = ip_failures.get(ip)
    if not rec:
        return False
    if rec.get('until') and time.time() < rec['until']:
        return True
    if rec.get('until') and time.time() >= rec['until']:
        ip_failures.pop(ip, None)
    return False


def record_ip_failure(ip):
    now = time.time()
    rec = ip_failures.setdefault(ip, {'count': 0, 'first': now, 'until': None})
    if now - rec['first'] > 600:
        rec['count'] = 0
        rec['first'] = now
    rec['count'] += 1
    if rec['count'] >= Config.IP_BLOCK_THRESHOLD and not rec.get('until'):
        rec['until'] = now + Config.IP_BLOCK_SECONDS
        log_event('IP_BLOCKED', 'ip', None, f"ip={ip} count={rec['count']}")
        try:
            db.execute_query(
                "INSERT INTO ip_blocks (ip_address, blocked_until, reason) VALUES (%s,%s,%s) "
                "ON CONFLICT (ip_address) DO UPDATE SET blocked_until=EXCLUDED.blocked_until",
                (ip, datetime.datetime.utcnow() + datetime.timedelta(seconds=Config.IP_BLOCK_SECONDS), 'threshold')
            )
        except Exception:
            pass


# ─── Cloudflare Turnstile CAPTCHA verification ───
# Replaces the old PIL-generated image CAPTCHA. The frontend widget posts a
# token under the field name 'cf-turnstile-response'; we verify that token
# server-side against Cloudflare's siteverify endpoint using CAPTCHA_SECRET
# from .env.
def captcha_ok(token, remote_ip=None):
    if not token:
        log.warning("Turnstile verify failed: token is empty")
        return False
    secret = os.getenv('CAPTCHA_SECRET', '').strip()
    if not secret or secret.startswith('CHANGE_ME'):
        log.error("CAPTCHA_SECRET not configured in .env or environment")
        print("[CRITICAL] CAPTCHA_SECRET is missing! Please configure it in .env or Render Dashboard Environment Variables.")
        return False
    try:
        payload = {
            'secret': secret,
            'response': token
        }
        # Only attach remoteip if it is a non-empty, public IP address (Cloudflare rejects empty or private IPs)
        if remote_ip and remote_ip not in ('127.0.0.1', 'localhost', '0.0.0.0') and not remote_ip.startswith('10.') and not remote_ip.startswith('192.168.') and not remote_ip.startswith('172.'):
            payload['remoteip'] = remote_ip

        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data=data,
            method='POST',
            headers={'User-Agent': 'ExpenseTracker-App/1.0'}
        )
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        success = bool(result.get('success'))
        if not success:
            err_codes = result.get('error-codes', [])
            log.warning(f"Turnstile verify failed: {err_codes}")
            print(f"[TURNSTILE] Verify failed with error codes: {err_codes}")
        return success
    except Exception as e:
        log.error(f"Turnstile verify request failed: {e}")
        print(f"[TURNSTILE EXCEPTION] {e}")
        return False


@app.route('/test')
def test():
    return jsonify({'message': 'Test route is working!'})


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


@app.route('/FRONTEND/HTML/<path:filename>')
def serve_frontend_html(filename):
    return serve_html(filename)


@app.route('/FRONTEND/CSS/<path:filename>')
def serve_frontend_css(filename):
    return serve_css(filename)


@app.route('/FRONTEND/JS/<path:filename>')
def serve_frontend_js(filename):
    return serve_js(filename)


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
            request.user_role = data.get('role', 'user')
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing!'}), 401
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            if data.get('role') != 'admin':
                log_event('ADMIN_ACCESS_DENIED', 'user_id', data.get('userId'),
                          f"path={request.path}")
                return jsonify({'error': 'Access denied'}), 403
            request.user_id = data['userId']
            request.user_email = data['email']
            request.user_role = 'admin'
            log_event('ADMIN_VIEWED_DASHBOARD', 'user_id', data.get('userId'),
                      f"path={request.path}")
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token!'}), 401
        return f(*args, **kwargs)
    return decorated


@app.route('/api/csrf-token', methods=['GET'])
def csrf_token():
    if not CSRF_AVAILABLE:
        return jsonify({'csrf_token': ''})
    return jsonify({'csrf_token': generate_csrf()})


@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json(silent=True) or {}

        turnstile_token = data.get('cf-turnstile-response') or data.get('captcha')
        if not captcha_ok(turnstile_token, client_ip()):
            log_event('CAPTCHA_FAILED', 'username', None, 'register')
            return jsonify({'error': 'CAPTCHA verification failed. Please try again.'}), 400

        if data.get('website'):
            return jsonify({'error': 'Registration failed.'}), 400

        if not data.get('consent'):
            return jsonify({'error': 'You must agree to the Privacy Notice to register.'}), 400

        id_number = (data.get('id_number') or '').strip()
        if not ID_RE.match(id_number):
            return jsonify({'error': 'ID Number must follow the format xxxx-xxxx.'}), 400

        errs = []
        for field, label in [('first_name','First Name'),
                             ('family_name','Family Name')]:
            e = validate_name(data.get(field,''), label)
            if e:
                errs.append(e)
        mn = data.get('middle_name')
        if mn and not mn.strip():
            mn = None
        elif mn:
            mn = mn.strip()
            e = validate_name(mn, 'Middle Name')
            if e:
                errs.append(e)
        if errs:
            return jsonify({'error': errs[0]}), 400

        birthdate = data.get('birthdate')
        age = compute_age(birthdate)
        if age is None:
            return jsonify({'error': 'Please enter a valid birthdate.'}), 400
        if age < 18:
            return jsonify({'error': 'You must be at least 18 years old to register.'}), 400

        for f in ['purok','barangay','municipality','province','region','postal_code']:
            if not data.get(f) or not str(data.get(f)).strip():
                return jsonify({'error': f'{f.replace("_"," ").title()} is required.'}), 400

        email = (data.get('email') or '').strip().lower()
        if not EMAIL_RE.match(email):
            return jsonify({'error': 'Please enter a valid email address.'}), 400

        username = (data.get('username') or '').strip()
        e = validate_username(username)
        if e:
            return jsonify({'error': e}), 400

        password = data.get('password') or ''
        e = validate_password(password)
        if e:
            return jsonify({'error': e}), 400

        if data.get('password') != data.get('confirm_password'):
            return jsonify({'error': 'Passwords do not match.'}), 400

        answers = data.get('answers') or {}
        answer_hashes = []
        for code, text in Config.AUTH_QUESTIONS:
            a = (answers.get(code) or '').strip()
            if len(a) < 2 or len(a) > 50:
                return jsonify({'error': f'Answer to "{text}" must be 2-50 characters.'}), 400
            if '  ' in a:
                return jsonify({'error': 'Double space is not allowed in answers.'}), 400
            answer_hashes.append((code, text, hash_answer(a)))

        tin_raw = (data.get('tin_number') or '').strip()
        if tin_raw and not re.match(r"^\d{3}-\d{3}-\d{3}-\d{3}$", tin_raw):
            return jsonify({'error': 'TIN must follow the format xxx-xxx-xxx-xxx.'}), 400
        income_bracket = data.get('income_bracket')
        allowed_brackets = ['<10k','10-20k','20-50k','50k+']
        if income_bracket not in allowed_brackets:
            return jsonify({'error': 'Please select a valid income bracket.'}), 400

        # Check existing accounts - allow unverified attempts to be replaced
        existing_email = db.execute_query("SELECT user_id, verified FROM users WHERE LOWER(email)=LOWER(%s)", (email,))
        if existing_email:
            if existing_email[0]['verified']:
                return jsonify({'error': 'This email is already registered.'}), 400
            else:
                db.execute_query("DELETE FROM users WHERE user_id=%s", (existing_email[0]['user_id'],))

        existing_id = db.execute_query("SELECT user_id, verified FROM users WHERE id_number=%s", (id_number,))
        if existing_id:
            if existing_id[0]['verified']:
                return jsonify({'error': 'This ID Number is already registered.'}), 400
            else:
                db.execute_query("DELETE FROM users WHERE user_id=%s", (existing_id[0]['user_id'],))

        existing_user = db.execute_query("SELECT user_id, verified FROM users WHERE LOWER(username)=LOWER(%s)", (username,))
        if existing_user:
            if existing_user[0]['verified']:
                return jsonify({'error': 'Username is already taken.'}), 400
            else:
                db.execute_query("DELETE FROM users WHERE user_id=%s", (existing_user[0]['user_id'],))

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        tin_enc = encrypt_field(tin_raw) if tin_raw else None

        date_joined = data.get('date_joined')
        if date_joined and not str(date_joined).strip():
            date_joined = None
        elif date_joined:
            date_joined = str(date_joined).strip()

        loan_purpose = data.get('loan_purpose')
        if loan_purpose and not str(loan_purpose).strip():
            loan_purpose = None
        elif loan_purpose:
            loan_purpose = str(loan_purpose).strip()

        name_ext = data.get('name_extension')
        if name_ext and not str(name_ext).strip():
            name_ext = None
        elif name_ext:
            name_ext = str(name_ext).strip()

        # NOTE: 'full_name' column does NOT exist in the users table (schema.sql),
        # so it is not included in this INSERT. Including it previously caused
        # a psycopg2 UndefinedColumn error -> "Registration failed".
        result = db.execute_query(
            """INSERT INTO users
               (id_number, first_name, middle_name, family_name, name_extension,
                birthdate, age, purok, barangay, municipality, province, region,
                postal_code, email, username, password_hash, role,
                tin_number_enc, income_bracket, date_joined, loan_purpose,
                currency, monthly_budget, consent_at, verified)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'user',
                       %s,%s,%s,%s,%s,%s,now(),FALSE)
               RETURNING user_id""",
            (id_number, data['first_name'].strip(), mn, data['family_name'].strip(),
             name_ext, birthdate, age,
             data['purok'].strip(), data['barangay'].strip(), data['municipality'].strip(),
             data['province'].strip(), data['region'].strip(), data['postal_code'].strip(),
             email, username, password_hash,
             tin_enc, income_bracket, date_joined,
             loan_purpose,
             data.get('currency','PHP'), float(data.get('monthly_budget') or 0))
        )
        user_id = dict(result[0])['user_id']

        for code, text, ah in answer_hashes:
            db.execute_query(
                "INSERT INTO security_questions (user_id, question_code, question_text, answer_hash) "
                "VALUES (%s,%s,%s,%s)",
                (user_id, code, text, ah)
            )
        db.execute_query(
            "INSERT INTO password_history (user_id, password_hash) VALUES (%s,%s)",
            (user_id, password_hash)
        )

        code, exp = create_otp(user_id, 'register')
        email_sent, email_err = send_otp_email(email, code, 'register')
        log_event('REGISTERED', 'username', user_id, f"email={email}")
        log_event('OTP_SENT', 'user_id', user_id, 'purpose=register')

        if email_sent:
            msg = f'Registration successful. Verification code has been sent to your Gmail ({email}). Please check your inbox and enter the code below (expires in 1 min).'
        else:
            msg = f'Registration successful. However, email could not be sent to {email}. Please verify Gmail SMTP in .env ({email_err or "SMTP not configured"}).'

        resp = {
            'message': msg,
            'email_sent': email_sent,
            'user': {'user_id': user_id, 'email': email, 'username': username,
                     'first_name': data['first_name'], 'family_name': data['family_name']}
        }
        return jsonify(resp), 201

    except Exception as e:
        log.error(f"Registration error: {e}", exc_info=True)
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/resend-registration-otp', methods=['POST'])
def resend_registration_otp():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({'error': 'Email is required.'}), 400

        row = db.execute_query("SELECT user_id, verified FROM users WHERE email=%s", (email,))
        if not row:
            return jsonify({'error': 'Account not found.'}), 404
        user = dict(row[0])
        if user.get('verified'):
            return jsonify({'error': 'Account is already verified. Please log in.'}), 400

        code, exp = create_otp(user['user_id'], 'register')
        email_sent, email_err = send_otp_email(email, code, 'register')
        log_event('OTP_RESENT', 'user_id', user['user_id'], 'purpose=register')

        if email_sent:
            msg = f'A new verification code has been sent to your Gmail ({email}). Please check your inbox (expires in 1 min).'
        else:
            msg = f'Could not send email to {email}. Please verify Gmail SMTP in .env ({email_err or "SMTP not configured"}).'

        resp = {'message': msg, 'email_sent': email_sent}
        return jsonify(resp)
    except Exception as e:
        log.error(f"Resend OTP error: {e}")
        return jsonify({'error': 'Failed to resend code.'}), 500


@app.route('/api/verify-registration', methods=['POST'])
def verify_registration():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').lower()
    code  = (data.get('code') or '').strip()
    row = db.execute_query("SELECT user_id, verified FROM users WHERE email=%s", (email,))
    if not row:
        return jsonify({'error': 'Account not found.'}), 404
    u = dict(row[0])
    if u.get('verified'):
        return jsonify({'message': 'Account is already verified. You may now log in.'})
    uid = u['user_id']
    ok, reason = verify_otp(uid, 'register', code)
    if not ok:
        if reason in ('expired', 'no_otp'):
            return jsonify({'error': 'Verification code has expired. Please click Resend Code to receive a new one.', 'expired': True}), 400
        return jsonify({'error': 'Invalid verification code. Please check your Gmail and try again.'}), 400
    db.execute_query("UPDATE users SET verified=TRUE WHERE user_id=%s", (uid,))
    log_event('ACCOUNT_VERIFIED', 'user_id', uid)
    return jsonify({'message': 'Account verified successfully! Your account is now fully created. Redirecting to log in...'})


@app.route('/api/login', methods=['POST'])
def login():
    try:
        ip = client_ip()
        if is_ip_blocked(ip):
            return jsonify({'error': 'Too many failures. Try again later.'}), 429

        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()

        email = (data.get('email') or '').strip().lower()
        password = data.get('password') or ''
        turnstile_token = data.get('cf-turnstile-response') or data.get('captcha')

        if not captcha_ok(turnstile_token, ip):
            log_event('CAPTCHA_FAILED', 'email', None, 'login')
            return jsonify({'error': 'CAPTCHA verification failed. Please try again.'}), 400

        if not email or not password:
            return jsonify({'error': 'Missing email or password'}), 400

        now = time.time()

        if email in login_attempts:
            rec = login_attempts[email]
            if rec.get('until') and now < rec['until']:
                remaining = int(rec['until'] - now)
                return jsonify({
                    'error': f'Account locked. Try again in {remaining} seconds.',
                    'locked_seconds': remaining,
                    'show_forgot': True,
                }), 429
            if rec.get('until') and now >= rec['until']:
                login_attempts[email] = {'count': 0, 'first': now, 'tier': 0, 'until': None}

        result = db.execute_query("SELECT * FROM users WHERE email=%s OR username=%s", (email, email))
        fail_common = lambda: _register_login_failure(email, ip)

        if not result:
            return fail_common()
        user = dict(result[0])

        if not bcrypt.checkpw(password.encode(), user['password_hash'].encode()):
            return fail_common()

        if not user.get('verified'):
            return jsonify({'error': 'Your account is not verified yet. Please enter the verification code sent to your email during registration to fully activate your account.'}), 403

        code, exp = create_otp(user['user_id'], 'login')
        email_sent, email_err = send_otp_email(user['email'], code, 'login')
        log_event('OTP_SENT', 'user_id', user['user_id'], 'purpose=login')

        if email in login_attempts:
            del login_attempts[email]

        if email_sent:
            msg = f'Password correct. Verification code has been sent to your Gmail ({user["email"]}). Please check your inbox and enter the code below (expires in 1 min).'
        else:
            msg = f'Password correct. However, email could not be sent to {user["email"]}. Please check Gmail SMTP settings in .env ({email_err or "SMTP not configured"}).'

        resp = {
            'message': msg,
            'otp_required': True,
            'email': user['email'],
            'email_sent': email_sent
        }
        return jsonify(resp)

    except Exception as e:
        log.error(f"Login error: {e}", exc_info=True)
        return jsonify({'error': 'Login failed'}), 500


def _register_login_failure(email, ip):
    now = time.time()
    rec = login_attempts.setdefault(email, {'count': 0, 'first': now, 'tier': 0, 'until': None})
    if now - rec['first'] > 600:
        rec.update({'count': 0, 'first': now, 'tier': 0, 'until': None})
    rec['count'] += 1
    record_ip_failure(ip)
    log_event('LOGIN_FAILED', 'email', None, f"email={email}")

    tier_seconds = {3: Config.LOCKOUT_TIER1_SECONDS,
                    6: Config.LOCKOUT_TIER2_SECONDS,
                    9: Config.LOCKOUT_TIER3_SECONDS}
    tier = 0
    if rec['count'] >= 9:
        tier = 3
    elif rec['count'] >= 6:
        tier = 2
    elif rec['count'] >= 3:
        tier = 1

    show_forgot = rec['count'] >= Config.FAILED_BEFORE_FORGOT

    if tier and tier > rec['tier']:
        rec['tier'] = tier
        rec['until'] = now + tier_seconds[tier]
        log_event(f'LOCKOUT_TIER_{tier}', 'email', None, f"email={email} count={rec['count']}")
        row = db.execute_query("SELECT email FROM users WHERE email=%s", (email,))
        if row:
            send_alert_email(dict(row[0])['email'], f'LOCKOUT_TIER_{tier}',
                             email, ip, request.headers.get('User-Agent',''), rec['count'])

    return jsonify({
        'error': 'Invalid email or password.',
        'show_forgot': show_forgot,
    }), 401


@app.route('/api/verify-login', methods=['POST'])
def verify_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').lower()
    code  = (data.get('code') or '').strip()
    row = db.execute_query("SELECT * FROM users WHERE email=%s", (email,))
    if not row:
        return jsonify({'error': 'Account not found.'}), 404
    user = dict(row[0])
    ok, reason = verify_otp(user['user_id'], 'login', code)
    if not ok:
        if reason in ('expired', 'no_otp'):
            return jsonify({'error': 'Verification code has expired. Please request a new code.', 'expired': True}), 400
        return jsonify({'error': 'Invalid verification code. Please check your Gmail and try again.'}), 400
    log_event('LOGIN_SUCCESS', 'user_id', user['user_id'])
    token = jwt.encode({
        'userId': user['user_id'],
        'email':  user['email'],
        'role':   user.get('role', 'user'),
        'exp':    datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    user.pop('password_hash', None)
    user.pop('tin_number_enc', None)
    return jsonify({'user': user, 'token': token, 'message': 'Login successful!'})


@app.route('/api/forgot/identify', methods=['POST'])
def forgot_identify():
    data = request.get_json(silent=True) or {}
    ident = (data.get('identifier') or '').strip().lower()
    if not captcha_ok(data.get('cf-turnstile-response'), client_ip()):
        log_event('CAPTCHA_FAILED', 'email', None, 'forgot')
        return jsonify({'error': 'CAPTCHA verification failed. Please try again.'}), 400
    rows = db.execute_query(
        "SELECT user_id FROM users WHERE email=%s OR username=%s", (ident, ident))
    if not rows:
        qs = [{'code': c, 'text': t} for c, t in Config.AUTH_QUESTIONS]
        return jsonify({'questions': qs})
    uid = dict(rows[0])['user_id']
    qrows = db.execute_query(
        "SELECT question_code, question_text FROM security_questions WHERE user_id=%s ORDER BY sq_id",
        (uid,))
    log_event('RESET_REQUESTED', 'user_id', uid)
    return jsonify({'questions': [dict(r) for r in qrows], 'identifier': ident})


@app.route('/api/forgot/answer', methods=['POST'])
def forgot_answer():
    data = request.get_json(silent=True) or {}
    ident = (data.get('identifier') or '').strip().lower()
    answers = data.get('answers') or {}
    rows = db.execute_query("SELECT user_id, email FROM users WHERE email=%s OR username=%s",
                            (ident, ident))
    if not rows:
        return jsonify({'error': 'Invalid answer.'}), 401
    user = dict(rows[0])
    qrows = db.execute_query(
        "SELECT question_code, answer_hash FROM security_questions WHERE user_id=%s",
        (user['user_id'],))
    for q in qrows:
        q = dict(q)
        submitted = answers.get(q['question_code'], '')
        if not check_answer(submitted, q['answer_hash']):
            log_event('LOGIN_FAILED', 'user_id', user['user_id'], 'forgot_answer')
            return jsonify({'error': 'Invalid answer.'}), 401
    code, exp = create_otp(user['user_id'], 'reset')
    email_sent, email_err = send_otp_email(user['email'], code, 'reset')
    log_event('OTP_SENT', 'user_id', user['user_id'], 'purpose=reset')
    reset_token = jwt.encode({
        'reset_user': user['user_id'],
        'purpose': 'reset',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.OTP_EXPIRY_MINUTES + 2)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    if email_sent:
        msg = f'Answer correct. Verification code has been sent to your Gmail ({user["email"]}). Please check your inbox and enter the code below (expires in 1 min).'
    else:
        msg = f'Answer correct. However, email could not be sent to {user["email"]}. Please check Gmail SMTP in .env ({email_err or "SMTP not configured"}).'

    resp = {
        'message': msg,
        'reset_token': reset_token,
        'email_sent': email_sent
    }
    return jsonify(resp)


@app.route('/api/forgot/verify', methods=['POST'])
def forgot_verify():
    data = request.get_json(silent=True) or {}
    token = data.get('reset_token')
    code  = (data.get('code') or '').strip()
    if not token:
        return jsonify({'error': 'Missing reset token.'}), 400
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except Exception:
        return jsonify({'error': 'Invalid or expired reset token.'}), 401
    uid = payload['reset_user']
    ok, reason = verify_otp(uid, 'reset', code)
    if not ok:
        if reason in ('expired', 'no_otp'):
            return jsonify({'error': 'Verification code has expired. Please request a new code.', 'expired': True}), 400
        return jsonify({'error': 'Invalid verification code. Please check your Gmail and try again.'}), 400
    change_token = jwt.encode({
        'change_user': uid,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=10)
    }, app.config['SECRET_KEY'], algorithm='HS256')
    return jsonify({'message': 'OTP verified.', 'change_token': change_token})


@app.route('/api/resend-forgot-otp', methods=['POST'])
def resend_forgot_otp():
    try:
        data = request.get_json(silent=True) or {}
        token = data.get('reset_token')
        if not token:
            return jsonify({'error': 'Missing reset token.'}), 400
        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except Exception:
            return jsonify({'error': 'Reset session expired. Please start over.'}), 401
        uid = payload['reset_user']
        row = db.execute_query("SELECT email FROM users WHERE user_id=%s", (uid,))
        if not row:
            return jsonify({'error': 'Account not found.'}), 404
        email = dict(row[0])['email']
        code, exp = create_otp(uid, 'reset')
        email_sent, email_err = send_otp_email(email, code, 'reset')
        log_event('OTP_SENT', 'user_id', uid, 'purpose=reset_resend')
        new_token = jwt.encode({
            'reset_user': uid,
            'purpose': 'reset',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.OTP_EXPIRY_MINUTES + 2)
        }, app.config['SECRET_KEY'], algorithm='HS256')
        if email_sent:
            msg = f'A new verification code has been sent to your Gmail ({email}). Please check your inbox (expires in 1 min).'
        else:
            msg = f'Could not send email to {email}. Please verify Gmail SMTP settings.'
        return jsonify({'message': msg, 'reset_token': new_token, 'email_sent': email_sent})
    except Exception as e:
        log.error(f"Resend forgot OTP error: {e}")
        return jsonify({'error': 'Failed to resend code.'}), 500


@app.route('/api/resend-login-otp', methods=['POST'])
def resend_login_otp():
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get('email') or '').strip().lower()
        if not email:
            return jsonify({'error': 'Missing email.'}), 400
        row = db.execute_query("SELECT user_id, email FROM users WHERE email=%s", (email,))
        if not row:
            return jsonify({'error': 'Account not found.'}), 404
        user = dict(row[0])
        code, exp = create_otp(user['user_id'], 'login')
        email_sent, email_err = send_otp_email(user['email'], code, 'login')
        log_event('OTP_SENT', 'user_id', user['user_id'], 'purpose=login_resend')
        if email_sent:
            msg = f'A new verification code has been sent to your Gmail ({user["email"]}). Please check your inbox (expires in 1 min).'
        else:
            msg = f'Could not send email to {user["email"]}. Please verify Gmail SMTP settings.'
        return jsonify({'message': msg, 'email_sent': email_sent})
    except Exception as e:
        log.error(f"Resend login OTP error: {e}")
        return jsonify({'error': 'Failed to resend code.'}), 500


@app.route('/api/change-password', methods=['POST'])
def change_password():
    data = request.get_json(silent=True) or {}
    token = data.get('change_token')
    new_pw = data.get('password') or ''
    confirm = data.get('confirm_password') or ''
    if not token:
        return jsonify({'error': 'Not authorized to change password.'}), 401
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
    except Exception:
        return jsonify({'error': 'Reset session expired.'}), 401
    uid = payload['change_user']
    if new_pw != confirm:
        return jsonify({'error': 'Passwords do not match.'}), 400
    e = validate_password(new_pw)
    if e:
        return jsonify({'error': e}), 400

    rows = db.execute_query(
        "SELECT password_hash FROM password_history WHERE user_id=%s ORDER BY id DESC LIMIT %s",
        (uid, Config.PASSWORD_HISTORY_DEPTH))
    for r in rows:
        if bcrypt.checkpw(new_pw.encode(), dict(r)['password_hash'].encode()):
            return jsonify({'error': 'You cannot reuse a recent password.'}), 400

    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
    db.execute_query("UPDATE users SET password_hash=%s WHERE user_id=%s", (new_hash, uid))
    db.execute_query("INSERT INTO password_history (user_id, password_hash) VALUES (%s,%s)",
                     (uid, new_hash))
    log_event('PASSWORD_CHANGED', 'user_id', uid)
    row = db.execute_query("SELECT email FROM users WHERE user_id=%s", (uid,))
    if row:
        send_alert_email(dict(row[0])['email'], 'PASSWORD_CHANGED',
                         str(uid), client_ip(), request.headers.get('User-Agent',''))
    return jsonify({'message': 'Successfully Change Password'})


@app.route('/api/username-available', methods=['GET'])
def username_available():
    u = (request.args.get('u') or '').strip()
    if not u:
        return jsonify({'available': False, 'error': 'Username is required.'})
    e = validate_username(u)
    if e:
        return jsonify({'available': False, 'error': e, 'invalid_format': True})
    # Check verified accounts only - unverified attempts can be overwritten
    rows = db.execute_query("SELECT 1 FROM users WHERE LOWER(username)=LOWER(%s) AND verified=TRUE", (u,))
    if rows:
        return jsonify({'available': False, 'taken': True, 'error': 'Username is already taken.'})
    return jsonify({'available': True})


@app.route('/api/categories', methods=['GET'])
@token_required
def get_categories():
    try:
        result = db.execute_query(
            "SELECT * FROM categories WHERE user_id = %s ORDER BY category_name",
            (request.user_id,))
        if not result:
            defaults = [
                ('Utilities', 'Expense'),
                ('Food & Groceries', 'Expense'),
                ('Transportation', 'Expense'),
                ('Rent & Housing', 'Expense'),
                ('Salary', 'Income')
            ]
            for cat_name, cat_type in defaults:
                try:
                    db.execute_query(
                        "INSERT INTO categories (user_id, category_name, category_type) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                        (request.user_id, cat_name, cat_type)
                    )
                except Exception:
                    pass
            result = db.execute_query(
                "SELECT * FROM categories WHERE user_id = %s ORDER BY category_name",
                (request.user_id,))
        return jsonify([dict(row) for row in result])
    except Exception as e:
        log.error(f"Get categories error: {e}")
        return jsonify({'error': 'Failed to fetch categories'}), 500


@app.route('/api/categories', methods=['POST'])
@token_required
def create_category():
    try:
        data = request.get_json(silent=True) or {}
        cat_name = (data.get('category_name') or '').strip()
        cat_type = (data.get('category_type') or 'Expense').strip()
        if not cat_name:
            return jsonify({'error': 'Category name is required'}), 400
        result = db.execute_query(
            """INSERT INTO categories (user_id, category_name, category_type)
               VALUES (%s, %s, %s)
               ON CONFLICT (user_id, category_name) DO UPDATE SET category_type = EXCLUDED.category_type
               RETURNING *""",
            (request.user_id, cat_name, cat_type))
        return jsonify(dict(result[0])), 201
    except Exception as e:
        log.error(f"Create category error: {e}")
        return jsonify({'error': 'Failed to create category'}), 500


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@token_required
def delete_category(category_id):
    try:
        db.execute_query(
            "DELETE FROM categories WHERE category_id = %s AND user_id = %s",
            (category_id, request.user_id))
        return jsonify({'message': 'Category deleted successfully'})
    except Exception as e:
        log.error(f"Delete category error: {e}")
        return jsonify({'error': 'Failed to delete category'}), 500


@app.route('/api/transactions', methods=['GET'])
@token_required
def get_transactions():
    try:
        result = db.execute_query(
            """SELECT t.*, COALESCE(c.category_name, 'Uncategorized') as category_name
               FROM transactions t
               LEFT JOIN categories c ON t.category_id = c.category_id
               WHERE t.user_id = %s
               ORDER BY t.transaction_date DESC, t.transaction_id DESC""",
            (request.user_id,))
        output = []
        for r in result:
            d = dict(r)
            if 'transaction_date' in d and d['transaction_date']:
                d['transaction_date'] = str(d['transaction_date'])
            if 'created_at' in d and d['created_at']:
                d['created_at'] = str(d['created_at'])
            if 'amount' in d and d['amount'] is not None:
                d['amount'] = float(d['amount'])
            output.append(d)
        return jsonify(output)
    except Exception as e:
        log.error(f"Get transactions error: {e}")
        return jsonify({'error': 'Failed to fetch transactions'}), 500


@app.route('/api/transactions', methods=['POST'])
@token_required
def create_transaction():
    try:
        data = request.get_json(silent=True) or {}
        cat_id = data.get('category_id')
        cat_name = data.get('category_name')
        
        # If category_id is missing or a name was passed, resolve or create it
        if not cat_id and cat_name:
            crows = db.execute_query(
                "SELECT category_id FROM categories WHERE user_id = %s AND LOWER(category_name) = LOWER(%s)",
                (request.user_id, cat_name.strip())
            )
            if crows:
                cat_id = crows[0]['category_id']
            else:
                cnew = db.execute_query(
                    "INSERT INTO categories (user_id, category_name, category_type) VALUES (%s,%s,%s) RETURNING category_id",
                    (request.user_id, cat_name.strip(), data.get('transaction_type', 'Expense'))
                )
                cat_id = cnew[0]['category_id']

        amount = float(data.get('amount') or 0)
        if amount <= 0:
            return jsonify({'error': 'Amount must be greater than zero'}), 400

        t_date = data.get('transaction_date') or datetime.date.today().isoformat()
        status = data.get('status') or 'Completed'
        recurrence = data.get('recurrence') or 'One-time'

        result = db.execute_query(
            """INSERT INTO transactions
               (user_id, category_id, transaction_type, amount, description, transaction_date, status, recurrence)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *""",
            (request.user_id, cat_id, data.get('transaction_type', 'Expense'),
             amount, data.get('description', '').strip(),
             t_date, status, recurrence))
        
        row = dict(result[0])
        if 'transaction_date' in row and row['transaction_date']:
            row['transaction_date'] = str(row['transaction_date'])
        if 'created_at' in row and row['created_at']:
            row['created_at'] = str(row['created_at'])
        if 'amount' in row and row['amount'] is not None:
            row['amount'] = float(row['amount'])
        return jsonify(row), 201
    except Exception as e:
        log.error(f"Create transaction error: {e}")
        return jsonify({'error': f'Failed to create transaction: {e}'}), 500


@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
@token_required
def update_transaction(transaction_id):
    try:
        data = request.get_json(silent=True) or {}
        status = data.get('status')
        t_date = data.get('transaction_date')
        if status:
            db.execute_query(
                "UPDATE transactions SET status = %s, transaction_date = COALESCE(%s, transaction_date) WHERE transaction_id = %s AND user_id = %s",
                (status, t_date, transaction_id, request.user_id))
        return jsonify({'message': 'Transaction updated successfully'})
    except Exception as e:
        log.error(f"Update transaction error: {e}")
        return jsonify({'error': 'Failed to update transaction'}), 500


@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
@token_required
def delete_transaction(transaction_id):
    try:
        db.execute_query(
            "DELETE FROM transactions WHERE transaction_id = %s AND user_id = %s",
            (transaction_id, request.user_id))
        return jsonify({'message': 'Transaction deleted successfully'})
    except Exception as e:
        log.error(f"Delete transaction error: {e}")
        return jsonify({'error': 'Failed to delete transaction'}), 500


@app.route('/api/budgets', methods=['GET'])
@token_required
def get_budgets():
    try:
        result = db.execute_query(
            """SELECT b.*, c.category_name FROM budgets b
               JOIN categories c ON b.category_id = c.category_id
               WHERE b.user_id = %s ORDER BY b.year DESC, b.month DESC""",
            (request.user_id,))
        output = []
        for r in result:
            d = dict(r)
            if 'amount' in d and d['amount'] is not None:
                d['amount'] = float(d['amount'])
            if 'created_at' in d and d['created_at']:
                d['created_at'] = str(d['created_at'])
            output.append(d)
        return jsonify(output)
    except Exception as e:
        log.error(f"Get budgets error: {e}")
        return jsonify({'error': 'Failed to fetch budgets'}), 500


@app.route('/api/budgets', methods=['POST'])
@token_required
def create_budget():
    try:
        data = request.get_json(silent=True) or {}
        cat_id = data.get('category_id')
        cat_name = data.get('category_name')
        if not cat_id and cat_name:
            crows = db.execute_query(
                "SELECT category_id FROM categories WHERE user_id = %s AND LOWER(category_name) = LOWER(%s)",
                (request.user_id, cat_name.strip())
            )
            if crows:
                cat_id = crows[0]['category_id']
            else:
                cnew = db.execute_query(
                    "INSERT INTO categories (user_id, category_name, category_type) VALUES (%s,%s,'Expense') RETURNING category_id",
                    (request.user_id, cat_name.strip())
                )
                cat_id = cnew[0]['category_id']

        amount = float(data.get('amount') or 0)
        month = int(data.get('month') or datetime.date.today().month)
        year = int(data.get('year') or datetime.date.today().year)

        result = db.execute_query(
            """INSERT INTO budgets (user_id, category_id, amount, month, year)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (user_id, category_id, month, year) DO UPDATE SET amount = EXCLUDED.amount
               RETURNING *""",
            (request.user_id, cat_id, amount, month, year))
        
        row = dict(result[0])
        if 'amount' in row and row['amount'] is not None:
            row['amount'] = float(row['amount'])
        return jsonify(row), 201
    except Exception as e:
        log.error(f"Create budget error: {e}")
        return jsonify({'error': 'Failed to create budget'}), 500


@app.route('/api/budgets/<int:budget_id>', methods=['DELETE'])
@token_required
def delete_budget(budget_id):
    try:
        db.execute_query(
            "DELETE FROM budgets WHERE budget_id = %s AND user_id = %s",
            (budget_id, request.user_id))
        return jsonify({'message': 'Budget deleted successfully'})
    except Exception as e:
        log.error(f"Delete budget error: {e}")
        return jsonify({'error': 'Failed to delete budget'}), 500


@app.route('/api/admin/summary', methods=['GET'])
@admin_required
def admin_summary():
    try:
        today = datetime.date.today()
        def count(ev):
            r = db.execute_query(
                "SELECT COUNT(*) AS c FROM activity_log WHERE event_type=%s AND created_at::date=%s",
                (ev, today))
            return int(dict(r[0])['c'])
        success = count('LOGIN_SUCCESS')
        failed  = count('LOGIN_FAILED')
        locks   = count('LOCKOUT_TIER_1') + count('LOCKOUT_TIER_2') + count('LOCKOUT_TIER_3')
        blocks  = count('IP_BLOCKED')
        otp_s   = count('OTP_SENT')
        otp_f   = count('OTP_FAILED')
        alerts  = count('ALERT_EMAIL_SENT')
        return jsonify({
            'successful_logins': success, 'failed_logins': failed,
            'accounts_locked': locks, 'ips_blocked': blocks,
            'otps_sent': otp_s, 'otp_failed': otp_f, 'alerts_sent': alerts
        })
    except Exception as e:
        log.error(f"admin_summary: {e}")
        return jsonify({'error': 'failed'}), 500


@app.route('/api/admin/failed-per-hour', methods=['GET'])
@admin_required
def admin_failed_per_hour():
    rows = db.execute_query(
        """SELECT date_trunc('hour', created_at) AS hr, COUNT(*) AS c
           FROM activity_log
           WHERE event_type='LOGIN_FAILED' AND created_at > now() - interval '24 hours'
           GROUP BY hr ORDER BY hr"""
    )
    return jsonify([{'hour': dict(r)['hr'].isoformat(), 'count': int(dict(r)['c'])} for r in rows])


@app.route('/api/admin/top-ips', methods=['GET'])
@admin_required
def admin_top_ips():
    rows = db.execute_query(
        """SELECT ip_address, COUNT(*) AS c
           FROM activity_log
           WHERE event_type='LOGIN_FAILED' AND created_at > now() - interval '24 hours'
           GROUP BY ip_address ORDER BY c DESC LIMIT 5"""
    )
    out = []
    for r in rows:
        r = dict(r)
        blk = db.execute_query(
            "SELECT 1 FROM ip_blocks WHERE ip_address=%s AND blocked_until > now()",
            (r['ip_address'],))
        out.append({'ip': str(r['ip_address']), 'failures': int(r['c']), 'blocked': bool(blk)})
    return jsonify(out)


@app.route('/api/admin/flags', methods=['GET'])
@admin_required
def admin_flags():
    rows = db.execute_query(
        "SELECT * FROM security_flags ORDER BY created_at DESC LIMIT 20")
    return jsonify([dict(r) for r in rows])


@app.route('/api/admin/events', methods=['GET'])
@admin_required
def admin_events():
    q = "SELECT * FROM activity_log WHERE 1=1"
    params = []
    if request.args.get('event'):
        q += " AND event_type=%s"
        params.append(request.args['event'])
    if request.args.get('ip'):
        q += " AND host(ip_address)=%s"
        params.append(request.args['ip'])
    if request.args.get('username'):
        q += " AND username_type=%s"
        params.append(request.args['username'])
    q += " ORDER BY created_at DESC LIMIT 50"
    rows = db.execute_query(q, tuple(params))
    out = []
    for r in rows:
        r = dict(r)
        for k, v in r.items():
            if isinstance(v, str):
                r[k] = html.escape(v)
        r['ip_address'] = str(r['ip_address']) if r['ip_address'] else None
        r['created_at'] = r['created_at'].isoformat() if r['created_at'] else None
        out.append(r)
    return jsonify(out)


common_passwords = [
    "1234", "12345", "123456", "12345678", "password", "password123",
    "admin", "admin123", "admin1234", "qwerty", "welcome", "student", "student123"
]
numeric_passwords = [str(i).zfill(6) for i in range(5001)]
password_list = list(dict.fromkeys(common_passwords + numeric_passwords))


def test_login(target_url, login_type, login_value, password):
    data = {}
    if login_type in ("username", "email"):
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
    path = os.path.join(BASE_DIR, 'lab_test.html')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            html_template = f.read()
    else:
        html_template = '<h1>lab_test.html missing</h1>'
    return render_template_string(html_template)


@app.route('/stream_test')
def stream_test():
    if 'start' not in request.args:
        return "Missing start parameter", 400
    target = request.args.get('target', 'http://localhost:5000/api/login')
    login_type = request.args.get('loginType', 'email')
    login_value = request.args.get('loginValue', '')
    if not login_value:
        return "Missing loginValue parameter.", 400
    def generate():
        start_time = time.time()
        attempt = 0
        yield "CYBER AUTHENTICATION LAB\n\n"
        for password in password_list:
            attempt += 1
            result = test_login(target, login_type, login_value, password)
            http_code = result["http_code"]
            if result.get("error"):
                yield f"[ERROR] {result['error']}\n"
                break
            if result["success"]:
                yield f"[{attempt:04d}] {password:<18} [HTTP {http_code}]  >>> SUCCESS <<<\n"
                break
            if http_code == 429:
                yield f"[{attempt:04d}] {password:<18} [HTTP 429]  LOCKED OUT\n"
                if attempt >= 25:
                    yield "[!] RATE LIMIT ACTIVE\n"
                    break
                continue
            yield f"[{attempt:04d}] {password:<18} [HTTP {http_code}]  FAILED\n"
            time.sleep(0.05)
    return Response(generate(), mimetype='text/plain')


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    log.error(f"500: {error}")
    return jsonify({'error': 'Internal server error'}), 500


if CSRF_AVAILABLE:
    @app.errorhandler(CSRFError)
    def csrf_error(e):
        log_event('CSRF_REJECTED', None, None, str(e))
        return jsonify({'error': 'CSRF token invalid or missing.'}), 400

    # Exempt JSON API routes so client fetch requests are not blocked by form CSRF
    for view_fn in [register, verify_registration, resend_registration_otp, login, verify_login, resend_login_otp,
                    forgot_identify, forgot_answer, forgot_verify, resend_forgot_otp, change_password,
                    create_category, delete_category, create_transaction, update_transaction, delete_transaction,
                    create_budget, delete_budget]:
        csrf.exempt(view_fn)

    # Initialize database tables if running for the first time
    try:
        db.init_db()
    except Exception as _e:
        log.warning(f"Initial DB setup note: {_e}")


if __name__ == '__main__':
    print("=" * 60)
    print("Starting Expense Tracker API...")
    print("=" * 60)
    print(f"Frontend folder: {FRONTEND_DIR}")
    print("API available at: http://localhost:5000/api/")
    print("Lab test: http://localhost:5000/lab_test")
    print("=" * 60)
    print("MODE: PROTECTED (locked, seeded values active)")
    print(f"Lockout tiers: {Config.LOCKOUT_TIER1_SECONDS}/{Config.LOCKOUT_TIER2_SECONDS}/{Config.LOCKOUT_TIER3_SECONDS} s")
    print(f"OTP: {Config.OTP_EXPIRY_MINUTES} min | Idle: {Config.IDLE_TIMEOUT_MINUTES} min")
    print("=" * 60)
    try:
        db.connect()
        app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)
    except Exception as e:
        print(f"Failed to start server: {e}")
    finally:
        db.close()