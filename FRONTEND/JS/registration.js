// ============================================
// REGISTRATION.JS - Registration Page Logic
// ============================================

function handleRegister(event) {
    event.preventDefault();
    
    var btn = document.getElementById('registerBtn');
    var alert = document.getElementById('registerAlert');
    var valid = true;
    
    // Validate required fields
    var requiredFields = ['regFullName', 'regEmail', 'regCurrency', 'regPassword', 'regConfirmPassword'];
    requiredFields.forEach(function(id) {
        var input = document.getElementById(id);
        if (!input) return;
        
        if (!input.value.trim()) {
            input.classList.add('error');
            var error = document.getElementById(id + 'Error');
            if (error) error.classList.add('show');
            valid = false;
        } else {
            validateField(id);
            if (input.classList.contains('error')) {
                valid = false;
            }
        }
    });
    
    // Validate budget
    if (!validateBudget()) {
        valid = false;
    }
    
    // Validate terms
    if (!validateTerms()) {
        valid = false;
    }
    
    if (!valid) {
        showAlert('registerAlert', 'Please fix the errors highlighted above.', 'error');
        return;
    }
    
    // Prepare data
    var userData = {
        full_name: document.getElementById('regFullName').value.trim(),
        email: document.getElementById('regEmail').value.trim(),
        password: document.getElementById('regPassword').value,
        currency: document.getElementById('regCurrency').value,
        monthly_budget: parseFloat(document.getElementById('regBudget').value) || 0
    };
    
    btn.disabled = true;
    btn.textContent = 'Creating account...';
    hideAlert('registerAlert');
    
    fetch(CONFIG.API_URL + '/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        btn.disabled = false;
        btn.textContent = 'Create Account';
        
        if (data.error) {
            showAlert('registerAlert', data.error, 'error');
            return;
        }
        
        saveAuthData(data.user, data.token);
        showAlert('registerAlert', 'Account created successfully!', 'success');
        
        setTimeout(function() {
            window.location.href = '/HTML/dashboard.html';
        }, 2000);
    })
    .catch(function(error) {
        btn.disabled = false;
        btn.textContent = 'Create Account';
        showAlert('registerAlert', 'Network error. Please try again.', 'error');
        console.error('Registration error:', error);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (isAuthenticated()) {
        window.location.href = '/HTML/dashboard.html';
    }
    
    // Password strength listener
    var passwordInput = document.getElementById('regPassword');
    if (passwordInput) {
        passwordInput.addEventListener('input', updatePasswordStrength);
    }
});

window.handleRegister = handleRegister;