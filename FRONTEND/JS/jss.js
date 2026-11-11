function switchTab(tab) {
    document.querySelectorAll('.tab-toggle button').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    document.querySelectorAll('.form-container').forEach(function(form) {
        form.classList.toggle('active', form.id === (tab === 'login' ? 'loginForm' : 'registerForm'));
    });
    document.getElementById('formTitle').textContent = tab === 'login' ? 'Sign In' : 'Create Account';
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
    var type = input.getAttribute('type') === 'password' ? 'text' : 'password';
    input.setAttribute('type', type);
    button.textContent = type === 'password' ? 'Show' : 'Hide';
}

document.addEventListener('DOMContentLoaded', function() {
    var passwordInput = document.getElementById('regPassword');
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            var password = this.value;
            var bar = document.getElementById('passwordStrengthBar');
            var text = document.getElementById('passwordStrengthText');
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
        });
    }

    var regFields = ['regFullName', 'regEmail', 'regCurrency', 'regPassword', 'regConfirmPassword'];
    regFields.forEach(function(id) {
        var input = document.getElementById(id);
        if (!input) return;
        input.addEventListener('blur', function() {
            validateField(id);
        });
        input.addEventListener('input', function() {
            if (this.classList.contains('error')) {
                validateField(id);
            }
        });
    });

    var budgetInput = document.getElementById('regBudget');
    if (budgetInput) {
        budgetInput.addEventListener('blur', function() {
            if (this.value && parseFloat(this.value) < 0) {
                this.classList.add('error');
                document.getElementById('regBudgetError').classList.add('show');
            } else {
                this.classList.remove('error');
                document.getElementById('regBudgetError').classList.remove('show');
            }
        });
    }
});

function validateField(id) {
    var input = document.getElementById(id);
    var error = document.getElementById(id + 'Error');
    if (!input || !error) return;
    var valid = true;
    switch (id) {
        case 'regFullName':
            valid = input.value.trim().length >= 2;
            error.textContent = 'Please enter your full name.';
            break;
        case 'regEmail':
            valid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(input.value.trim());
            error.textContent = 'Please enter a valid email address.';
            break;
        case 'regCurrency':
            valid = input.value !== '';
            error.textContent = 'Please select your preferred currency.';
            break;
        case 'regPassword':
            valid = input.value.length >= 8;
            error.textContent = 'Password must be at least 8 characters.';
            break;
        case 'regConfirmPassword':
            var pwd = document.getElementById('regPassword').value;
            valid = input.value === pwd && input.value.length > 0;
            error.textContent = 'Passwords do not match.';
            break;
        default:
            return;
    }
    input.classList.toggle('error', !valid && input.value.length > 0);
    input.classList.toggle('success', valid && input.value.length > 0);
    error.classList.toggle('show', !valid && input.value.length > 0);
}

function handleLogin(event) {
    event.preventDefault();
    var email = document.getElementById('loginEmail');
    var password = document.getElementById('loginPassword');
    var alert = document.getElementById('loginAlert');
    var btn = document.getElementById('loginBtn');
    var valid = true;
    if (!email.value.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
        email.classList.add('error');
        document.getElementById('loginEmailError').classList.add('show');
        valid = false;
    } else {
        email.classList.remove('error');
        document.getElementById('loginEmailError').classList.remove('show');
    }
    if (!password.value.trim()) {
        password.classList.add('error');
        document.getElementById('loginPasswordError').classList.add('show');
        valid = false;
    } else {
        password.classList.remove('error');
        document.getElementById('loginPasswordError').classList.remove('show');
    }
    if (!valid) return;
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    alert.classList.remove('show');
    setTimeout(function() {
        btn.disabled = false;
        btn.textContent = 'Log In';
        alert.className = 'alert alert-success show';
        alert.innerHTML = 'Welcome back!';
        setTimeout(function() {
            alert.classList.remove('show');
        }, 3000);
    }, 1500);
}

function handleRegister(event) {
    event.preventDefault();
    var btn = document.getElementById('registerBtn');
    var alert = document.getElementById('registerAlert');
    var fields = ['regFullName', 'regEmail', 'regCurrency', 'regPassword', 'regConfirmPassword'];
    var valid = true;
    fields.forEach(function(id) {
        validateField(id);
        var input = document.getElementById(id);
        if (input && input.classList.contains('error')) {
            valid = false;
        }
        if (input && !input.value.trim()) {
            input.classList.add('error');
            var error = document.getElementById(id + 'Error');
            if (error) error.classList.add('show');
            valid = false;
        }
    });
    var budget = document.getElementById('regBudget');
    var budgetError = document.getElementById('regBudgetError');
    if (budget.value && parseFloat(budget.value) < 0) {
        budget.classList.add('error');
        budgetError.classList.add('show');
        valid = false;
    } else {
        budget.classList.remove('error');
        budgetError.classList.remove('show');
    }
    var terms = document.getElementById('termsCheck');
    var termsError = document.getElementById('termsError');
    if (!terms.checked) {
        termsError.classList.add('show');
        valid = false;
    } else {
        termsError.classList.remove('show');
    }
    if (!valid) {
        alert.className = 'alert alert-error show';
        alert.innerHTML = 'Please fix the errors highlighted above.';
        return;
    }
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    alert.classList.remove('show');
    setTimeout(function() {
        btn.disabled = false;
        btn.textContent = 'Create Account';
        alert.className = 'alert alert-success show';
        alert.innerHTML = 'Account created successfully!';
        document.getElementById('registerFormElement').reset();
        document.querySelectorAll('.input-wrapper input').forEach(function(inp) {
            inp.classList.remove('success', 'error');
        });
        document.querySelectorAll('.error-message').forEach(function(msg) {
            msg.classList.remove('show');
        });
        document.getElementById('passwordStrengthBar').style.width = '0%';
        document.getElementById('passwordStrengthText').textContent = 'Weak';
        document.getElementById('passwordStrengthText').style.color = '#606770';
        document.getElementById('termsError').classList.remove('show');
        setTimeout(function() {
            alert.classList.remove('show');
            switchTab('login');
        }, 3000);
    }, 2000);
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        var activeForm = document.querySelector('.form-container.active form');
        if (activeForm) {
            activeForm.dispatchEvent(new Event('submit'));
        }
    }
});