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

window.getUser = getUser;
window.getToken = getToken;
window.isAuthenticated = isAuthenticated;
window.saveAuthData = saveAuthData;
window.clearAuthData = clearAuthData;
window.logout = logout;