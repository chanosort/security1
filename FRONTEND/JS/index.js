// ============================================
// INDEX.JS - Login Page Logic
// Includes Cloudflare Turnstile CAPTCHA, OTP step, lockout countdown
// ============================================

var pendingEmail = '';

function handleLogin(event) {
    event.preventDefault();

    var email = document.getElementById('loginEmail');
    var password = document.getElementById('loginPassword');
    var alertEl = document.getElementById('loginAlert');
    var btn = document.getElementById('loginBtn');
    var forgotLink = document.getElementById('forgotLink');
    var lockoutBanner = document.getElementById('lockoutBanner');

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

    // Get Cloudflare Turnstile token
    var turnstileInput = document.querySelector('[name="cf-turnstile-response"]');
    var turnstileToken = turnstileInput ? turnstileInput.value : '';
    if (!turnstileToken) {
        showAlert('loginAlert', 'Please complete the CAPTCHA verification.', 'error');
        return;
    }

    btn.disabled = true;
    btn.textContent = 'Signing in...';
    alertEl.classList.remove('show');

    fetch(CONFIG.API_URL + '/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: email.value.trim(),
            password: password.value,
            'cf-turnstile-response': turnstileToken
        })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        btn.disabled = false;
        btn.textContent = 'Log In';
        // Reset Turnstile widget after each attempt
        if (window.turnstile) window.turnstile.reset();

        if (data.show_forgot && forgotLink) {
            forgotLink.style.display = 'inline';
        }

        if (data.locked_seconds) {
            if (lockoutBanner) {
                lockoutBanner.style.display = 'block';
                var remaining = data.locked_seconds;
                btn.disabled = true;
                var timer = setInterval(function() {
                    lockoutBanner.textContent = 'Account locked. Try again in ' + remaining + ' s.';
                    if (--remaining <= 0) {
                        clearInterval(timer);
                        lockoutBanner.style.display = 'none';
                        btn.disabled = false;
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
            var msg = data.message || 'Verification code sent to your Gmail. Please check your inbox and enter it below (expires in 1 min).';
            showAlert('otpAlert', msg, 'success');
            startLoginOtpTimer(60);
        } else if (data.token) {
            saveAuthData(data.user, data.token);
            showAlert('loginAlert', 'Login successful!', 'success');
            setTimeout(function() { window.location.href = '/HTML/dashboard.html'; }, 1200);
        }
    })
    .catch(function(error) {
        btn.disabled = false;
        btn.textContent = 'Log In';
        showAlert('loginAlert', 'Network error. Please try again.', 'error');
        console.error('Login error:', error);
    });
}

var loginOtpTimerInterval = null;

function startLoginOtpTimer(durationSeconds) {
    if (loginOtpTimerInterval) clearInterval(loginOtpTimerInterval);
    var remaining = durationSeconds || 60;
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
                timerEl.innerHTML = '<span style="color: #c0392b; font-weight: 700;">Code expired (1 min limit). Click Resend Code below.</span>';
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
    fetch(CONFIG.API_URL + '/resend-login-otp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: pendingEmail })
    })
    .then(function(r) { return r.json(); })
    .then(function(data) {
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Code';
        }
        if (data.error) {
            showAlert('otpAlert', data.error, 'error');
            if (resendBtn) resendBtn.style.display = 'block';
            return;
        }
        var codeInput = document.getElementById('otpCode');
        if (codeInput) {
            codeInput.value = '';
            codeInput.focus();
        }
        showAlert('otpAlert', data.message || 'New verification code sent to your Gmail!', 'success');
        startLoginOtpTimer(60);
    })
    .catch(function(err) {
        if (resendBtn) {
            resendBtn.disabled = false;
            resendBtn.textContent = 'Resend Code';
            resendBtn.style.display = 'block';
        }
        showAlert('otpAlert', 'Network error while requesting new code.', 'error');
    });
}

function handleOtp(event) {
    event.preventDefault();
    var code = document.getElementById('otpCode').value.trim();
    var btn = document.getElementById('loginVerifyBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Verifying...';
    }
    fetch(CONFIG.API_URL + '/verify-login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: pendingEmail, code: code })
    })
    .then(function(response) { return response.json(); })
    .then(function(data) {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Verify Code';
        }
        if (data.error) {
            showAlert('otpAlert', data.error, 'error');
            var resendBtn = document.getElementById('resendLoginOtpBtn');
            if (resendBtn) resendBtn.style.display = 'block';
            return;
        }
        if (loginOtpTimerInterval) clearInterval(loginOtpTimerInterval);
        saveAuthData(data.user, data.token);
        showAlert('otpAlert', data.message, 'success');
        setTimeout(function() { window.location.href = '/HTML/dashboard.html'; }, 900);
    })
    .catch(function() {
        if (btn) {
            btn.disabled = false;
            btn.textContent = 'Verify Code';
        }
        showAlert('otpAlert', 'Network error.', 'error');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (isAuthenticated()) {
        window.location.href = '/HTML/dashboard.html';
    }
    document.querySelectorAll('.form-group input').forEach(function(input) {
        input.addEventListener('blur', function() {
            if (this.value) this.classList.remove('error');
        });
    });
});

window.handleLogin = handleLogin;
window.handleOtp = handleOtp;
window.handleResendLoginOtp = handleResendLoginOtp;