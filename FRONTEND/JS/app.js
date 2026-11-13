// ============================================
// APP.JS - Main Entry Point
// ============================================

document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        var activeForm = document.querySelector('.form-container.active form');
        if (activeForm && document.activeElement && document.activeElement.tagName === 'INPUT') {
            // Skip if active element is inside a multi-step flow form (handled inline)
            if (!document.getElementById('otpForm') || document.getElementById('otpForm').style.display === 'none') {
                activeForm.dispatchEvent(new Event('submit'));
            }
        }
    }
});

console.log('ExpenseTracker App Loaded');