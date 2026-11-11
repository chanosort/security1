// ============================================
// APP.JS - Main Entry Point
// ============================================

document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
        var activeForm = document.querySelector('.form-container.active form');
        if (activeForm) {
            activeForm.dispatchEvent(new Event('submit'));
        }
    }
});

console.log('Finance Tracker App Loaded');