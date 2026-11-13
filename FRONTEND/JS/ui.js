// ============================================
// UI HELPER FUNCTIONS - Shared
// ============================================

function switchTab(tab) {
    document.querySelectorAll('.form-container').forEach(function(form) {
        form.classList.remove('active');
    });
    if (tab === 'login') {
        var loginForm = document.getElementById('loginForm');
        if (loginForm) loginForm.classList.add('active');
    } else {
        var registerForm = document.getElementById('registerForm');
        if (registerForm) registerForm.classList.add('active');
    }
}

function togglePassword(inputId, button) {
    var input = document.getElementById(inputId);
    if (!input) return;
    var type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    button.textContent = type === 'password' ? 'Show' : 'Hide';
}

// Password strength meter (handout 4.9) - Weak / Medium / Strong
function updatePasswordStrength() {
    var passwordInput = document.getElementById('regPassword');
    if (!passwordInput) return;

    var password = passwordInput.value;
    var bar = document.getElementById('regPasswordStrengthBar');
    var text = document.getElementById('regPasswordStrengthText');

    if (!bar) return;

    var score = 0;
    if (password.length >= CONFIG.MIN_PASSWORD) score++;
    if (password.length >= 14) score++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^a-zA-Z0-9]/.test(password)) score++;

    var percentage = Math.min((score / 5) * 100, 100);
    bar.style.width = percentage + '%';

    var label = 'Weak';
    var cls = 'weak';
    if (score >= 4) { label = 'Strong'; cls = 'strong'; }
    else if (score >= 2) { label = 'Medium'; cls = 'medium'; }

    bar.className = 'bar ' + cls;
    if (text) {
        text.textContent = password.length === 0 ? '' : label;
        text.className = 'strength-text';
    }
}

function showAlert(elementId, message, type) {
    var alert = document.getElementById(elementId);
    if (!alert) return;
    alert.className = 'alert alert-' + type + ' show';
    alert.innerHTML = message;
}

function hideAlert(elementId) {
    var alert = document.getElementById(elementId);
    if (alert) {
        alert.classList.remove('show');
        alert.innerHTML = '';
    }
}

function refreshCaptcha(imgId) {
    var img = document.getElementById(imgId);
    var baseUrl = (typeof CONFIG !== 'undefined' && CONFIG.API_URL) ? CONFIG.API_URL : '/api';
    if (img) img.src = baseUrl + '/captcha?_=' + Date.now();
}

function escapeHtml(value) {
    return String(value == null ? '' : value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

window.switchTab = switchTab;
window.togglePassword = togglePassword;
window.updatePasswordStrength = updatePasswordStrength;
window.showAlert = showAlert;
window.hideAlert = hideAlert;
window.refreshCaptcha = refreshCaptcha;
window.escapeHtml = escapeHtml;