// ============================================
// VALIDATION FUNCTIONS - Shared
// Matches server-side rules from handout section 4.5, 4.9
// ============================================

var NAME_REGEX = /^[A-Z][a-z']*(?: [A-Z][a-z']*)*$/;
var ID_REGEX = /^\d{4}-\d{4}$/;
var EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
var TIN_REGEX = /^\d{3}-\d{3}-\d{3}-\d{3}$/;

function validateNameField(value, label) {
    if (!value || !value.trim()) return label + ' is required.';
    value = value.trim();
    if (value.length < 2 || value.length > CONFIG.MAX_NAME_FIELD)
        return label + ' must be 2-' + CONFIG.MAX_NAME_FIELD + ' characters.';
    if (/\d/.test(value)) return 'Numbers are not allowed in ' + label + '.';
    if (/[^A-Za-z ']/.test(value)) return 'Special characters are not allowed in ' + label + '.';
    if (/  /.test(value)) return 'Double space is not allowed.';
    if (value === value.toUpperCase() && value.length > 1)
        return 'Do not use all capital letters.';
    if (/(.)\1\1/i.test(value)) return 'Three consecutive identical letters are not allowed.';
    if (!NAME_REGEX.test(value)) return 'First letter of ' + label + ' must be capital.';
    return null;
}

function validateField(id) {
    var input = document.getElementById(id);
    var error = document.getElementById(id + 'Error');
    if (!input) return;
    var msg = '';

    switch (id) {
        case 'regIdNumber':
            msg = ID_REGEX.test(input.value.trim()) ? '' : 'ID Number must follow the format xxxx-xxxx.';
            break;
        case 'regFirstName':
            msg = validateNameField(input.value, 'First Name') || '';
            break;
        case 'regMiddleName':
            if (input.value.trim()) msg = validateNameField(input.value, 'Middle Name') || '';
            break;
        case 'regFamilyName':
            msg = validateNameField(input.value, 'Family Name') || '';
            break;
        case 'regEmail':
            msg = EMAIL_REGEX.test(input.value.trim()) ? '' : 'Please enter a valid email address.';
            break;
        case 'regUsername':
            var u = input.value.trim();
            if (!u) msg = 'Username is required.';
            else if (!/^[A-Za-z][A-Za-z0-9]*$/.test(u))
                msg = 'Username must start with a letter and contain only letters and digits.';
            else if (u.length < CONFIG.MIN_USERNAME || u.length > CONFIG.MAX_USERNAME)
                msg = 'Username must be ' + CONFIG.MIN_USERNAME + '-' + CONFIG.MAX_USERNAME + ' characters.';
            break;
        case 'regPassword':
            if (!input.value) msg = 'Password is required.';
            else if (input.value.length < CONFIG.MIN_PASSWORD)
                msg = 'Password must be at least ' + CONFIG.MIN_PASSWORD + ' characters.';
            else if (input.value.length > CONFIG.MAX_PASSWORD)
                msg = 'Password must be at most ' + CONFIG.MAX_PASSWORD + ' characters.';
            break;
        case 'regConfirmPassword':
            var pwd = document.getElementById('regPassword');
            if (pwd && input.value !== pwd.value) msg = 'Passwords do not match.';
            break;
        case 'regBirthdate':
            if (!input.value) msg = 'Birthdate is required.';
            else {
                var bd = new Date(input.value);
                var t = new Date();
                var age = t.getFullYear() - bd.getFullYear();
                var m = t.getMonth() - bd.getMonth();
                if (m < 0 || (m === 0 && t.getDate() < bd.getDate())) age--;
                if (bd > t) msg = 'Birthdate cannot be in the future.';
                else if (age < 18) msg = 'You must be at least 18 years old to register.';
            }
            break;
        case 'regTin':
            if (!input.value.trim()) msg = 'TIN is required.';
            else if (!TIN_REGEX.test(input.value.trim()))
                msg = 'TIN must follow the format xxx-xxx-xxx-xxx.';
            break;
        case 'regPurok':
            if (!input.value.trim()) msg = 'Purok is required.';
            break;
        case 'regBarangay':
            if (!input.value.trim()) msg = 'Barangay is required.';
            break;
        case 'regMunicipality':
            if (!input.value.trim()) msg = 'Municipality / City is required.';
            break;
        case 'regProvince':
            if (!input.value.trim()) msg = 'Province is required.';
            break;
        case 'regRegion':
            if (!input.value.trim()) msg = 'Region is required.';
            break;
        case 'regPostal':
            if (!input.value.trim()) msg = 'Postal code is required.';
            break;
        case 'regIncome':
            if (!input.value) msg = 'Please select an income bracket.';
            break;
        case 'regQ4':
        case 'regQ7':
        case 'regQ1':
            var a = input.value.trim();
            if (!a) msg = 'Please answer this security question.';
            else if (a.length < 2 || a.length > 50) msg = 'Answer must be 2-50 characters.';
            else if (/  /.test(a)) msg = 'Double space is not allowed.';
            break;
        case 'regCaptcha':
            if (!input.value.trim()) msg = 'Please enter the CAPTCHA characters.';
            break;
        case 'regConsent':
            if (!input.checked) msg = 'You must agree to the Privacy Notice to register.';
            break;
        default:
            return;
    }

    input.classList.toggle('error', !!msg);
    input.closest('.form-group') && input.closest('.form-group').classList.toggle('error', !!msg);
    if (error) {
        error.textContent = msg;
        error.classList.toggle('show', !!msg);
    }
}

function validateBudget() {
    var budget = document.getElementById('regBudget');
    var error = document.getElementById('regBudgetError');
    if (!budget || !error) return true;
    if (budget.value && parseFloat(budget.value) < 0) {
        budget.classList.add('error');
        error.classList.add('show');
        return false;
    }
    budget.classList.remove('error');
    error.classList.remove('show');
    return true;
}

function validateTerms() {
    var terms = document.getElementById('regConsent');
    if (!terms) return true;
    return terms.checked;
}

window.validateNameField = validateNameField;
window.validateField = validateField;
window.validateBudget = validateBudget;
window.validateTerms = validateTerms;