// ============================================
// JSS.JS - combined login/register tab helper
// Keeps tab-based switching if you use the combined page
// ============================================

function switchTab(tab) {
    document.querySelectorAll('.tab-toggle button').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.form-container').forEach(function(form) {
        form.classList.toggle('active', form.id === (tab === 'login' ? 'loginForm' : 'registerForm'));
    });
    var title = document.getElementById('formTitle');
    if (title) title.textContent = tab === 'login' ? 'Sign In' : 'Create Account';
    document.querySelectorAll('.alert').forEach(function(a) {
        a.classList.remove('show');
        a.textContent = '';
    });
    document.querySelectorAll('.input-wrapper input').forEach(function(input) {
        input.classList.remove('error', 'success');
    });
    document.querySelectorAll('.error-message').forEach(function(msg) {
        msg.classList.remove('show');
    });
}

function togglePassword(inputId, button) {
    var input = document.getElementById(inputId);
    if (!input) return;
    var type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    button.textContent = type === 'password' ? 'Show' : 'Hide';
}

// The heavy lifting is handled in index.js and registration.js.
// This file keeps the combined login/register tab page working.

window.switchTab = switchTab;
window.togglePassword = togglePassword;