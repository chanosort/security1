// ============================================
// VALIDATION FUNCTIONS - Shared
// ============================================

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

function validateBudget() {
    var budget = document.getElementById('regBudget');
    var error = document.getElementById('regBudgetError');
    if (!budget || !error) return true;
    
    if (budget.value && parseFloat(budget.value) < 0) {
        budget.classList.add('error');
        error.classList.add('show');
        return false;
    } else {
        budget.classList.remove('error');
        error.classList.remove('show');
        return true;
    }
}

function validateTerms() {
    var terms = document.getElementById('termsCheck');
    var error = document.getElementById('termsError');
    if (!terms || !error) return true;
    
    if (!terms.checked) {
        error.classList.add('show');
        return false;
    } else {
        error.classList.remove('show');
        return true;
    }
}

window.validateField = validateField;
window.validateBudget = validateBudget;
window.validateTerms = validateTerms;