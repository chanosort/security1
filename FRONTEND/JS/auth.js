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
        window.location.replace('/HTML/index.html');
    }
}

// Handout §8.4: Session & Back button protection
// Ensures hitting browser Back button after logout never displays protected page
window.addEventListener('pageshow', function(event) {
    if (window.location.pathname.includes('dashboard.html')) {
        if (!isAuthenticated()) {
            window.location.replace('/HTML/index.html');
        }
    }
});

// ============================================
// SESSION AUTO LOG-OUT (10 seconds, regardless of cursor movement)
// Shows in-page warning banner 5 seconds before logging out (no alert popup)
// ============================================
var _sessionStart = Date.now();

function showSessionWarning(secsLeft) {
    var warnBox = document.getElementById('idleWarningModal');
    if (!warnBox) {
        warnBox = document.createElement('div');
        warnBox.id = 'idleWarningModal';
        warnBox.style.cssText = 'position:fixed;top:20px;right:20px;z-index:99999;background:#fff3cd;color:#856404;border:1px solid #ffeeba;padding:15px 20px;border-radius:10px;box-shadow:0 4px 14px rgba(0,0,0,0.16);font-size:14px;font-weight:700;max-width:340px;';
        document.body.appendChild(warnBox);
    }
    warnBox.textContent = '⚠️ Session Warning: You will be logged out in ' + secsLeft + ' s.';
    warnBox.style.display = 'block';
}

function initIdleTimeout() {
    if (!isAuthenticated()) return;
    _sessionStart = Date.now();

    var timer = setInterval(function() {
        if (!isAuthenticated()) {
            clearInterval(timer);
            return;
        }
        var timeoutSec = (typeof CONFIG !== 'undefined' && CONFIG.SESSION_TIMEOUT_SECONDS) ? CONFIG.SESSION_TIMEOUT_SECONDS : 10;
        var timeoutMs = timeoutSec * 1000;
        var warnMs = Math.max(0, timeoutMs - 5000); // show warning 5s before logout
        var elapsed = Date.now() - _sessionStart;

        if (elapsed >= timeoutMs) {
            clearInterval(timer);
            clearAuthData();
            window.location.replace('/HTML/index.html');
        } else if (elapsed >= warnMs) {
            var secsLeft = Math.max(1, Math.ceil((timeoutMs - elapsed) / 1000));
            showSessionWarning(secsLeft);
        }
    }, 500);
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