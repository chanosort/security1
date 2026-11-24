// ============================================
// INDEX.JS - Login Page Logic
// Includes Google reCAPTCHA v2, OTP step, lockout countdown, CSRF
// ============================================

var pendingEmail = '';
var loginOtpTimerInterval = null;
var resendCooldownInterval = null;

window._recaptchaToken = '';
window.onRecaptchaSuccess = function(token) {
    window._recaptchaToken = token;
    var alertEl = document.getElementById('loginAlert');
    if (alertEl && alertEl.textContent && alertEl.textContent.indexOf('CAPTCHA') !== -1) {
        alertEl.classList.remove('show');
    }
};
window.onRecaptchaExpired = function() {
    window._recaptchaToken = '';
};

function getLoginCaptchaToken() {
    if (window._recaptchaToken) return window._recaptchaToken;
    if (typeof grecaptcha !== 'undefined' && grecaptcha.getResponse) {
        var resp = grecaptcha.getResponse();
        if (resp) return resp;
    }
    var el = document.querySelector('[name="g-recaptcha-response"]');
    if (el && el.value) return el.value;
    return '';
}

function fetchCsrfToken() {
    fetch('/api/csrf-token')
        .then(function(r) { return r.json(); })
        .then(function(data) {
            if (data.csrf_token) {
                var el = document.getElementById('csrfToken');
                if (el) el.value = data.csrf_token;
                var elOtp = document.getElementById('csrfTokenOtp');
                if (elOtp) elOtp.value = data.csrf_token;
            }
        })
        .catch(function(e) { /* ignore */ });
}

var isLoggingIn = false;

function handleLogin(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (isLoggingIn) return;

    var email = document.getElementById('loginEmail');
    var password = document.getElementById('loginPassword');
    var alertEl = document.getElementById('loginAlert');
    var btn = document.getElementById('loginBtn');
    var forgotLink = document.getElementById('forgotLink');
    var createAccountLink = document.getElementById('createAccountLink') || document.querySelector('a[href*="registration.html"]');
    var lockoutBanner = document.getElementById('lockoutBanner');
    var csrfInput = document.getElementById('csrfToken');
    var csrfToken = csrfInput ? csrfInput.value : '';

    if (!email.value.trim()) {
        email.classList.add('error');
        document.getElementById('loginEmailError').classList.add('show');
        return;
    }
    if (!password.value) {
        password.classList.add('error');
        document.getElementById('loginPasswordError').classList.add('show');
        return;
    }

    // Read Google reCAPTCHA v2 token immediately
    var recaptchaToken = getLoginCaptchaToken();
    if (!recaptchaToken) {
        showAlert('loginAlert', 'Please complete the CAPTCHA verification.', 'error');
        return;
    }

    isLoggingIn = true;
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    alertEl.classList.remove('show');

    fetch(CONFIG.API_URL + '/login', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify({
            email: email.value.trim(),
            password: password.value,
            'g-recaptcha-response': recaptchaToken,
            'captcha': recaptchaToken,
            'csrf_token': csrfToken
        })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        isLoggingIn = false;
        btn.disabled = false;
        btn.textContent = 'Log In';

        // Reset Google reCAPTCHA widget after each attempt
        if (typeof grecaptcha !== 'undefined' && grecaptcha.reset) {
            grecaptcha.reset();
        }
        window._recaptchaToken = '';

        // Section 8.2 & User Request: Make Forgot Password and Create Account visible after wrong username/password
        var formFooter = document.getElementById('loginFormFooter');
        if (formFooter) formFooter.style.display = 'flex';
        if (forgotLink) forgotLink.style.display = 'inline';
        if (createAccountLink) createAccountLink.style.display = 'inline';

        if (data.locked_seconds) {
            if (lockoutBanner) {
                lockoutBanner.style.display = 'block';
                var remaining = data.locked_seconds;
                btn.disabled = true;
                if (createAccountLink) {
                    createAccountLink.style.pointerEvents = 'none';
                    createAccountLink.style.opacity = '0.5';
                }
                var timer = setInterval(function() {
                    lockoutBanner.textContent = 'Account locked. Try again in ' + remaining + ' s.';
                    if (--remaining <= 0) {
                        clearInterval(timer);
                        lockoutBanner.style.display = 'none';
                        btn.disabled = false;
                        if (createAccountLink) {
                            createAccountLink.style.pointerEvents = 'auto';
                            createAccountLink.style.opacity = '1';
                        }
                    }
                }, 1000);
            }
            return;
        }

        if (data.error) {
            showAlert('loginAlert', data.error, 'error');
            return;
        }

        if (data.otp_required) {
            pendingEmail = data.email;
            document.getElementById('loginFormElement').style.display = 'none';
            document.getElementById('otpForm').style.display = 'block';
            var codeInput = document.getElementById('otpCode');
            if (codeInput) {
                codeInput.value = '';
                codeInput.focus();
            }
            startLoginOtpTimer(CONFIG.OTP_EXPIRY_MINUTES * 60);
            showAlert('otpAlert', data.message, 'success');
            return;
        }

        showAlert('loginAlert', 'Unexpected response from server.', 'error');
    })
    .catch(function(err) {
        isLoggingIn = false;
        btn.disabled = false;
        btn.textContent = 'Log In';
        if (typeof grecaptcha !== 'undefined' && grecaptcha.reset) {
            grecaptcha.reset();
        }
        window._recaptchaToken = '';
        showAlert('loginAlert', 'Connection error. Please try again.', 'error');
    });
}

function startLoginOtpTimer(durationSeconds) {
    if (loginOtpTimerInterval) clearInterval(loginOtpTimerInterval);
    var remaining = durationSeconds || (CONFIG.OTP_EXPIRY_MINUTES * 60) || 300;
    var timerEl = document.getElementById('loginOtpTimer');
    var resendBtn = document.getElementById('resendLoginOtpBtn');
    var verifyBtn = document.getElementById('loginVerifyBtn');

    if (resendBtn) resendBtn.style.display = 'none';
    if (verifyBtn) verifyBtn.disabled = false;
    if (timerEl) {
        timerEl.style.display = 'block';
        timerEl.style.color = 'var(--green-700, #20864f)';
    }

    function render() {
        var mins = Math.floor(remaining / 60);
        var secs = remaining % 60;
        var display = (mins < 10 ? '0' : '') + mins + ':' + (secs < 10 ? '0' : '') + secs;
        var countEl = document.getElementById('loginOtpCountdown');
        if (countEl) countEl.textContent = display;

        if (remaining <= 0) {
            clearInterval(loginOtpTimerInterval);
            if (timerEl) {
                timerEl.innerHTML = '<span style="color: #c0392b; font-weight: 700;">Code expired (5 min limit). Click Resend Code below.</span>';
            }
            if (resendBtn) resendBtn.style.display = 'block';
        }
        remaining--;
    }
    render();
    loginOtpTimerInterval = setInterval(render, 1000);
}

function handleResendLoginOtp() {
    var resendBtn = document.getElementById('resendLoginOtpBtn');
    if (resendBtn) {
        resendBtn.disabled = true;
        resendBtn.textContent = 'Sending new code...';
    }
    var csrfInput = document.getElementById('csrfTokenOtp') || document.getElementById('csrfToken');
    var csrfToken = csrfInput ? csrfInput.value : '';

    fetch(CONFIG.API_URL + '/resend-login-otp', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify({ email: pendingEmail, csrf_token: csrfToken })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (data.error) {
            showAlert('otpAlert', data.error, 'error');
            if (resendBtn) {
                resendBtn.disabled = false;
                resendBtn.textContent = 'Resend Code';
            }
            return;
        }

        showAlert('otpAlert', data.message || 'New verification code sent.', 'success');
        startLoginOtpTimer(CONFIG.OTP_EXPIRY_MINUTES * 60);

        // Section 6.2 rule 6: 60-second cooldown with visible countdown
        if (resendBtn) {
            var cooldown = 60;
            resendBtn.disabled = true;
            if (resendCooldownInterval) clearInterval(resendCooldownInterval);
            resendCooldownInterval = setInterval(function() {
                resendBtn.textContent = 'Resend in ' + cooldown + 's';
                if (--cooldown < 0) {
                    clearInterval(resendCooldownInterval);
                    resendBtn.disabled = false;
                    resendBtn.textContent = 'Resend Code';
                }
            }, 1000);
        }
    })
    .catch(function() {
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Code';
        }
        showAlert('otpAlert', 'Failed to resend verification code.', 'error');
    });
}

function handleOtp(event) {
    event.preventDefault();
    var code = (document.getElementById('otpCode').value || '').trim();
    var btn = document.getElementById('loginVerifyBtn');
    var alertEl = document.getElementById('otpAlert');
    var csrfInput = document.getElementById('csrfTokenOtp') || document.getElementById('csrfToken');
    var csrfToken = csrfInput ? csrfInput.value : '';

    if (!code || code.length !== 6) {
        showAlert('otpAlert', 'Please enter the 6-digit verification code.', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Verifying...';

    fetch(CONFIG.API_URL + '/verify-login', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify({
            email: pendingEmail,
            code: code,
            csrf_token: csrfToken
        })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        btn.disabled = false;
        btn.textContent = 'Verify Code';

        if (data.error) {
            showAlert('otpAlert', data.error, 'error');
            var resendBtn = document.getElementById('resendLoginOtpBtn');
            if (data.locked || data.expired) {
                if (resendBtn) resendBtn.style.display = 'block';
            }
            return;
        }

        saveAuthData(data.user, data.token);
        showAlert('otpAlert', data.message || 'Log-in successful!', 'success');
        setTimeout(function() { window.location.href = '/HTML/dashboard.html'; }, 900);
    })
    .catch(function() {
        btn.disabled = false;
        btn.textContent = 'Verify Code';
        showAlert('otpAlert', 'Network error.', 'error');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (isAuthenticated()) {
        window.location.href = '/HTML/dashboard.html';
    }
    fetchCsrfToken();
    document.querySelectorAll('.form-group input').forEach(function(input) {
        input.addEventListener('input', function() {
            if (this.value) {
                this.classList.remove('error');
                var err = document.getElementById(this.id + 'Error');
                if (err) err.classList.remove('show');
            }
        });
        input.addEventListener('blur', function() {
            if (this.value) {
                this.classList.remove('error');
                var err = document.getElementById(this.id + 'Error');
                if (err) err.classList.remove('show');
            }
        });
    });
});

window.handleLogin = handleLogin;
window.handleOtp = handleOtp;
window.handleResendLoginOtp = handleResendLoginOtp;
