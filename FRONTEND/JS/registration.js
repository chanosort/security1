// ============================================
// REGISTRATION.JS - Registration Page Logic
// Handles all core + system fields, CAPTCHA, consent, OTP timer & resend
// ============================================

var pendingRegisterEmail = '';
var otpTimerInterval = null;

function handleRegister(event) {
    if (event) event.preventDefault();

    var btn = document.getElementById('registerBtn');
    var alertEl = document.getElementById('registerAlert');

    // All required field IDs (Turnstile CAPTCHA is validated separately)
    var requiredIds = [
        'regIdNumber', 'regFirstName', 'regFamilyName', 'regBirthdate',
        'regPurok', 'regBarangay', 'regMunicipality', 'regProvince',
        'regRegion', 'regPostal', 'regEmail', 'regUsername',
        'regPassword', 'regConfirmPassword', 'regQ4', 'regQ7', 'regQ1',
        'regTin', 'regIncome', 'regConsent'
    ];

    var valid = true;
    requiredIds.forEach(function(id) {
        var input = document.getElementById(id);
        if (!input) {
            valid = false;
            return;
        }
        if (typeof validateField === 'function') {
            validateField(id);
        }
        if (input.classList.contains('error')) {
            valid = false;
        } else if (input.type === 'checkbox' && !input.checked) {
            valid = false;
        } else if (input.type !== 'checkbox' && !input.value.trim()) {
            input.classList.add('error');
            var errEl = document.getElementById(id + 'Error');
            if (errEl && !errEl.textContent) {
                errEl.textContent = 'This field is required.';
                errEl.classList.add('show');
            }
            valid = false;
        }
    });

    if (typeof validateBudget === 'function' && !validateBudget()) {
        valid = false;
    }

    if (!valid) {
        showAlert('registerAlert', 'Please check the highlighted fields above and correct all errors.', 'error');
        // Smoothly scroll to the first field with an error so user immediately sees what is needed
        var firstError = document.querySelector('.form-group.error, .error-message.show, input.error, select.error');
        if (firstError) {
            firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            var focusEl = (firstError.tagName === 'INPUT' || firstError.tagName === 'SELECT')
                ? firstError
                : firstError.querySelector('input, select');
            if (focusEl && typeof focusEl.focus === 'function') {
                focusEl.focus();
            }
        }
        return;
    }

    // Name extension
    var nameExtEl = document.getElementById('regNameExt');
    var nameExtSel = nameExtEl ? nameExtEl.value : '';
    var nameExtOtherEl = document.getElementById('regNameExtOther');
    var nameExt = (nameExtSel === 'Other' && nameExtOtherEl)
        ? nameExtOtherEl.value.trim()
        : nameExtSel;

    var getVal = function(id) {
        var el = document.getElementById(id);
        return el ? el.value.trim() : '';
    };

    var consentEl = document.getElementById('regConsent');

    // Get Cloudflare Turnstile token
    var turnstileInput = document.querySelector('[name="cf-turnstile-response"]');
    var turnstileToken = turnstileInput ? turnstileInput.value : '';
    if (!turnstileToken) {
        showAlert('registerAlert', 'Please complete the CAPTCHA verification.', 'error');
        var topAlert = document.getElementById('registerAlert');
        if (topAlert) topAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
    }

    var payload = {
        website: getVal('website'),
        id_number: getVal('regIdNumber'),
        first_name: getVal('regFirstName'),
        middle_name: getVal('regMiddleName'),
        family_name: getVal('regFamilyName'),
        name_extension: nameExt,
        birthdate: document.getElementById('regBirthdate') ? document.getElementById('regBirthdate').value : '',
        purok: getVal('regPurok'),
        barangay: getVal('regBarangay'),
        municipality: getVal('regMunicipality'),
        province: getVal('regProvince'),
        region: getVal('regRegion'),
        postal_code: getVal('regPostal'),
        email: getVal('regEmail').toLowerCase(),
        username: getVal('regUsername'),
        password: document.getElementById('regPassword') ? document.getElementById('regPassword').value : '',
        confirm_password: document.getElementById('regConfirmPassword') ? document.getElementById('regConfirmPassword').value : '',
        answers: {
            Q4: getVal('regQ4'),
            Q7: getVal('regQ7'),
            Q1: getVal('regQ1')
        },
        tin_number: getVal('regTin'),
        income_bracket: document.getElementById('regIncome') ? document.getElementById('regIncome').value : '',
        monthly_budget: parseFloat(getVal('regBudget')) || 0,
        currency: 'PHP',
        captcha: captchaEl ? captchaEl.value.trim() : '',
        consent: !!(consentEl && consentEl.checked)
    };

    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Creating account...';
    }
    hideAlert('registerAlert');

    fetch(CONFIG.API_URL + '/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
    })
    .then(function(response) {
        return response.json().then(function(data) {
            return { ok: response.ok, status: response.status, data: data };
        }).catch(function() {
            return { ok: response.ok, status: response.status, data: { error: 'Invalid response from server.' } };
        });
    })
    .then(function(res) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
        var data = res.data;

        if (!res.ok || data.error) {
            var errMsg = data.error || 'Registration failed. Please try again.';
            showAlert('registerAlert', errMsg, 'error');
            var topAlert = document.getElementById('registerAlert');
            if (topAlert) topAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
            if (typeof refreshCaptcha === 'function') refreshCaptcha('captchaImg');
            // Reset Turnstile widget on error
            if (window.turnstile) window.turnstile.reset();
            return;
        }

        pendingRegisterEmail = payload.email;

        // Transition to verification form
        var regForm = document.getElementById('registerFormElement');
        var verifyForm = document.getElementById('verifyFormElement');
        var verifyEmailInput = document.getElementById('verifyEmail');

        if (verifyForm && regForm) {
            regForm.style.display = 'none';
            verifyForm.style.display = 'block';
            if (verifyEmailInput) verifyEmailInput.value = pendingRegisterEmail;

            var codeInput = document.getElementById('verifyCode');
            if (codeInput) {
                codeInput.value = ''; // Always empty - user must check Gmail
                codeInput.focus();
            }

            var successMsg = data.message || 'Registration successful. A verification code has been sent to your Gmail (expires in 1 min). Please check your email and enter the code below.';
            showAlert('verifyAlert', successMsg, 'success');
            verifyForm.scrollIntoView({ behavior: 'smooth', block: 'start' });

            // Start 1-minute countdown timer
            startOtpTimer(60);
        } else {
            showAlert('registerAlert', data.message || 'Registration successful. Check your email for verification code.', 'success');
        }
    })
    .catch(function(error) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Create Account';
        }
        showAlert('registerAlert', 'Network error. Please make sure the backend server is running.', 'error');
        var topAlert = document.getElementById('registerAlert');
        if (topAlert) topAlert.scrollIntoView({ behavior: 'smooth', block: 'center' });
        console.error('Registration error:', error);
    });
}

function startOtpTimer(durationSeconds) {
    if (otpTimerInterval) clearInterval(otpTimerInterval);
    var remaining = durationSeconds || 60;
    var timerEl = document.getElementById('otpTimer');
    var resendBtn = document.getElementById('resendOtpBtn');
    var verifyBtn = document.getElementById('verifyBtn');

    if (resendBtn) resendBtn.style.display = 'none';
    if (verifyBtn) verifyBtn.disabled = false;
    if (timerEl) {
        timerEl.style.display = 'block';
        timerEl.style.color = 'var(--green-700)';
    }

    function render() {
        var mins = Math.floor(remaining / 60);
        var secs = remaining % 60;
        var display = (mins < 10 ? '0' : '') + mins + ':' + (secs < 10 ? '0' : '') + secs;
        if (timerEl) {
            timerEl.innerHTML = 'Code expires in: <span id="countdown" style="font-weight:700;">' + display + '</span>';
        }

        if (remaining <= 0) {
            clearInterval(otpTimerInterval);
            if (timerEl) {
                timerEl.innerHTML = '<span style="color: #c0392b; font-weight: 700;">Verification code expired (1 minute passed). Please request a new code.</span>';
            }
            if (resendBtn) resendBtn.style.display = 'block';
        }
        remaining--;
    }

    render();
    otpTimerInterval = setInterval(render, 1000);
}

function handleResendOtp() {
    var email = pendingRegisterEmail || (document.getElementById('verifyEmail') ? document.getElementById('verifyEmail').value.trim() : '');
    if (!email) {
        showAlert('verifyAlert', 'No email found. Please return to registration.', 'error');
        return;
    }
    var resendBtn = document.getElementById('resendOtpBtn');
    if (resendBtn) {
        resendBtn.disabled = true;
        resendBtn.textContent = 'Sending new code...';
    }

    fetch(CONFIG.API_URL + '/resend-registration-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Code';
        }
        if (data.error) {
            showAlert('verifyAlert', data.error, 'error');
            return;
        }
        var codeInput = document.getElementById('verifyCode');
        if (codeInput) {
            codeInput.value = ''; // Always empty - user must check Gmail
            codeInput.focus();
        }
        var msg = data.message || 'New verification code sent to your Gmail! It will expire in 1 minute.';
        showAlert('verifyAlert', msg, 'success');
        startOtpTimer(60);
    })
    .catch(function(err) {
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Code';
        }
        showAlert('verifyAlert', 'Network error while requesting new code. Please try again.', 'error');
        console.error('Resend OTP error:', err);
    });
}

function handleVerifyOtp(event) {
    if (event) event.preventDefault();

    var email = pendingRegisterEmail || (document.getElementById('verifyEmail') ? document.getElementById('verifyEmail').value.trim() : '');
    var codeInput = document.getElementById('verifyCode');
    var code = codeInput ? codeInput.value.trim() : '';

    if (!email) {
        showAlert('verifyAlert', 'Missing email. Please register again.', 'error');
        return;
    }
    if (!code) {
        showAlert('verifyAlert', 'Please enter the 6-digit verification code.', 'error');
        if (codeInput) codeInput.focus();
        return;
    }

    submitVerification(email, code);
}

function submitVerification(email, code) {
    var alertId = document.getElementById('verifyFormElement') && document.getElementById('verifyFormElement').style.display !== 'none'
        ? 'verifyAlert'
        : 'registerAlert';

    var btn = document.getElementById('verifyBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Verifying...';
    }

    fetch(CONFIG.API_URL + '/verify-registration', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email, code: code })
    })
    .then(function(r) { return r.json(); })
    .then(function(v) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Verify Account';
        }
        if (v.error) {
            showAlert(alertId, v.error, 'error');
            var resendBtn = document.getElementById('resendOtpBtn');
            if (resendBtn) resendBtn.style.display = 'block';
            return;
        }
        if (otpTimerInterval) clearInterval(otpTimerInterval);
        showAlert(alertId, v.message + ' Redirecting to log in...', 'success');
        setTimeout(function() {
            window.location.href = 'index.html';
        }, 1200);
    })
    .catch(function(err) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Verify Account';
        }
        showAlert(alertId, 'Network error. Please try again.', 'error');
        console.error('Verification error:', err);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (typeof isAuthenticated === 'function' && isAuthenticated()) {
        window.location.href = 'dashboard.html';
        return;
    }

    var passwordInput = document.getElementById('regPassword');
    if (passwordInput && typeof updatePasswordStrength === 'function') {
        passwordInput.addEventListener('input', updatePasswordStrength);
    }

    // Live validation
    var liveFields = [
        'regIdNumber','regFirstName','regMiddleName','regFamilyName','regEmail',
        'regUsername','regPassword','regConfirmPassword','regBirthdate','regTin',
        'regPurok','regBarangay','regMunicipality','regProvince','regRegion',
        'regPostal','regIncome','regQ4','regQ7','regQ1','regConsent'
    ];

    liveFields.forEach(function(id) {
        var input = document.getElementById(id);
        if (!input) return;
        input.addEventListener('blur', function() {
            if (typeof validateField === 'function') validateField(id);
        });
        input.addEventListener('input', function() {
            if (this.classList.contains('error') && typeof validateField === 'function') {
                validateField(id);
            }
        });
        input.addEventListener('change', function() {
            if (typeof validateField === 'function') validateField(id);
        });
    });

    // Live username availability
    var uname = document.getElementById('regUsername');
    if (uname) {
        uname.addEventListener('blur', function() {
            var u = this.value.trim();
            if (!u || u.length < (CONFIG.MIN_USERNAME || 7)) return;
            fetch(CONFIG.API_URL + '/username-available?u=' + encodeURIComponent(u), { credentials: 'include' })
                .then(function(r) { return r.json(); })
                .then(function(j) {
                    var err = document.getElementById('regUsernameError');
                    if (!err) return;
                    if (!j.available) {
                        uname.classList.add('error');
                        err.textContent = 'Username is already taken.';
                        err.classList.add('show');
                    } else if (err.textContent === 'Username is already taken.') {
                        uname.classList.remove('error');
                        err.classList.remove('show');
                        err.textContent = '';
                    }
                })
                .catch(function() {});
        });
    }

    // Auto age calculation (FIXED: uses b.getDate() instead of bd.getDate())
    var bd = document.getElementById('regBirthdate');
    if (bd) {
        var updateAge = function() {
            var age = document.getElementById('regAge');
            if (!age) return;
            if (!bd.value) { age.value = ''; return; }
            var b = new Date(bd.value);
            var t = new Date();
            var a = t.getFullYear() - b.getFullYear();
            var m = t.getMonth() - b.getMonth();
            if (m < 0 || (m === 0 && t.getDate() < b.getDate())) a--;
            age.value = a >= 0 ? a : '';
        };
        bd.addEventListener('change', updateAge);
        bd.addEventListener('input', updateAge);
    }

    // Name extension Other
    var ext = document.getElementById('regNameExt');
    if (ext) {
        ext.addEventListener('change', function() {
            var other = document.getElementById('regNameExtOther');
            if (other) {
                other.style.display = this.value === 'Other' ? 'block' : 'none';
                if (this.value !== 'Other') other.value = '';
            }
        });
    }
});

window.handleRegister = handleRegister;
window.handleVerifyOtp = handleVerifyOtp;
window.handleResendOtp = handleResendOtp;
window.submitVerification = submitVerification;
window.startOtpTimer = startOtpTimer;
