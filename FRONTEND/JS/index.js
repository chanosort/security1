// ============================================
// INDEX.JS - Login Page Logic
// ============================================

function handleLogin(event) {
    event.preventDefault();
    
    var email = document.getElementById('loginEmail');
    var password = document.getElementById('loginPassword');
    var alert = document.getElementById('loginAlert');
    var btn = document.getElementById('loginBtn');
    
    // Validate
    if (!email.value.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())) {
        email.classList.add('error');
        document.getElementById('loginEmailError').classList.add('show');
        return;
    }
    if (!password.value.trim()) {
        password.classList.add('error');
        document.getElementById('loginPasswordError').classList.add('show');
        return;
    }
    
    btn.disabled = true;
    btn.textContent = 'Signing in...';
    alert.classList.remove('show');
    
    fetch(CONFIG.API_URL + '/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            email: email.value.trim(),
            password: password.value
        })
    })
    .then(function(response) {
        return response.json();
    })
    .then(function(data) {
        btn.disabled = false;
        btn.textContent = 'Log In';
        
        if (data.error) {
            alert.className = 'alert alert-error show';
            alert.innerHTML = data.error;
            return;
        }
        
        saveAuthData(data.user, data.token);
        alert.className = 'alert alert-success show';
        alert.innerHTML = 'Login successful!';
        
        setTimeout(function() {
            window.location.href = '/HTML/dashboard.html';
        }, 1500);
    })
    .catch(function(error) {
        btn.disabled = false;
        btn.textContent = 'Log In';
        alert.className = 'alert alert-error show';
        alert.innerHTML = 'Network error. Please try again.';
        console.error('Login error:', error);
    });
}

document.addEventListener('DOMContentLoaded', function() {
    if (isAuthenticated()) {
        window.location.href = '/HTML/dashboard.html';
    }
});

window.handleLogin = handleLogin;