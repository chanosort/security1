// ============================================
// CONFIGURATION - Shared across all pages
// ExpenseTracker System
// ============================================

var apiOrigin = window.location.origin;
// Use current origin for deployed environments (Render, etc.)
// Fall back to localhost only when running directly from a file or local dev server on a different port
if (!apiOrigin || apiOrigin === 'null' || apiOrigin.startsWith('file:') || apiOrigin.includes(':5500') || apiOrigin.includes(':3000')) {
    apiOrigin = 'http://localhost:5000';
}
// Strip trailing slash if any
apiOrigin = apiOrigin.replace(/\/$/, '');

var CONFIG = {
    // API base URL
    API_URL: apiOrigin + '/api',

    // LocalStorage keys
    TOKEN_KEY: 'token',
    USER_KEY: 'user',

    // Security constants
    MIN_USERNAME: 6,           // Min username length: 6 characters
    MAX_USERNAME: 20,          // Max username length: 20 characters
    MIN_PASSWORD: 8,           // Min password length: 8 characters
    MAX_PASSWORD: 64,          // Handout max: 64 characters
    MAX_NAME_FIELD: 50,        // Max length of each name field: 50 characters
    FAILED_BEFORE_FORGOT: 2,   // Failed log-ins before "Forgot Password?" appears: 2

    // Lockout tiers in seconds
    LOCKOUT_TIER1: 15,         // Lockout tier 1 (3 failed log-ins): 15 seconds
    LOCKOUT_TIER2: 30,         // Lockout tier 2 (3 more): 30 seconds
    LOCKOUT_TIER3: 60,         // Lockout tier 3 (3 more): 60 seconds

    // OTP and session
    OTP_EXPIRY_MINUTES: 5,     // OTP expiry: 5 minutes
    IDLE_TIMEOUT_MINUTES: 15,  // Idle session timeout: 15 minutes

    // IP blocking
    IP_BLOCK_THRESHOLD: 10,    // IP block threshold (failures in 10 minutes, any account): 10
    IP_BLOCK_SECONDS: 600      // 10 minutes
};

window.CONFIG = CONFIG;