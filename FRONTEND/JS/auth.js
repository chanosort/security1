// ============================================
// AUTHENTICATION FUNCTIONS - Shared
// ============================================

function getUser() {
    var user = localStorage.getItem(CONFIG.USER_KEY);
    return user ? JSON.parse(user) : null;
}

function getToken() {
    return localStorage.getItem(CONFIG.TOKEN_KEY);
}

function isAuthenticated() {
    return !!getToken();
}

function saveAuthData(user, token) {
    localStorage.setItem(CONFIG.TOKEN_KEY, token);
    localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
}

function clearAuthData() {
    localStorage.removeItem(CONFIG.TOKEN_KEY);
    localStorage.removeItem(CONFIG.USER_KEY);
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        clearAuthData();
        window.location.href = '/HTML/index.html';
    }
}

// ============================================
// IDLE SESSION TIMEOUT (Handout §8.4: 15 min, warn 1 min before)
// ============================================
var _lastActivity = Date.now();
var _idleWarned = false;

function resetIdleTimer() {
    _lastActivity = Date.now();
    _idleWarned = false;
    var warnBox = document.getElementById('idleWarningModal');
    if (warnBox) warnBox.style.display = 'none';
}

function initIdleTimeout() {
    if (!isAuthenticated()) return;

    ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'].forEach(function(evt) {
        window.addEventListener(evt, resetIdleTimer, { passive: true });
    });

    setInterval(function() {
        if (!isAuthenticated()) return;
        var timeoutMs = (CONFIG.IDLE_TIMEOUT_MINUTES || 15) * 60 * 1000;
        var warnMs = timeoutMs - (60 * 1000); // 1 minute before timeout
        var elapsed = Date.now() - _lastActivity;

        if (elapsed >= timeoutMs) {
            clearAuthData();
            alert('Your session has expired due to 15 minutes of inactivity. You have been logged out.');
            window.location.href = '/HTML/index.html';
        } else if (elapsed >= warnMs && !_idleWarned) {
            _idleWarned = true;
            showIdleWarning();
        }
    }, 5000);
}

function showIdleWarning() {
    var warnBox = document.getElementById('idleWarningModal');
    if (!warnBox) {
        warnBox = document.createElement('div');
        warnBox.id = 'idleWarningModal';
        warnBox.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;background:#fff3cd;color:#856404;border:1px solid #ffeeba;padding:15px 20px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.15);font-size:14px;font-weight:600;max-width:320px;';
        warnBox.innerHTML = '⚠️ Inactivity Warning: You will be logged out in 1 minute due to inactivity. Move your mouse or click anywhere to stay signed in.';
        document.body.appendChild(warnBox);
    }
    warnBox.style.display = 'block';
}

document.addEventListener('DOMContentLoaded', function() {
    initIdleTimeout();
});

function authHeaders(extra) {
    var headers = extra || {};
    var token = getToken();
    if (token) headers['Authorization'] = 'Bearer ' + token;
    return headers;
}

window.getUser = getUser;
window.getToken = getToken;
window.isAuthenticated = isAuthenticated;
window.saveAuthData = saveAuthData;
window.clearAuthData = clearAuthData;
window.logout = logout;
window.authHeaders = authHeaders;