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

function updatePasswordStrength() {
    var passwordInput = document.getElementById('regPassword');
    if (!passwordInput) return;
    
    var password = passwordInput.value;
    var bar = document.getElementById('passwordStrengthBar');
    var text = document.getElementById('passwordStrengthText');
    
    if (!bar || !text) return;
    
    var strength = 0;
    if (password.length >= 8) strength += 1;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^a-zA-Z0-9]/.test(password)) strength += 1;
    
    var percentage = (strength / 4) * 100;
    bar.style.width = percentage + '%';
    
    if (strength >= 4) {
        bar.style.background = '#31a24c';
        text.textContent = 'Strong';
        text.style.color = '#31a24c';
    } else if (strength >= 3) {
        bar.style.background = '#f39c12';
        text.textContent = 'Good';
        text.style.color = '#f39c12';
    } else if (strength >= 2) {
        bar.style.background = '#f1c40f';
        text.textContent = 'Fair';
        text.style.color = '#f1c40f';
    } else {
        bar.style.background = '#f02849';
        text.textContent = 'Weak';
        text.style.color = '#f02849';
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

window.switchTab = switchTab;
window.togglePassword = togglePassword;
window.updatePasswordStrength = updatePasswordStrength;
window.showAlert = showAlert;
window.hideAlert = hideAlert;