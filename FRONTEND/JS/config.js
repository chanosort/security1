// ============================================
// CONFIGURATION - Shared across all pages
// ExpenseTracker System
// Seed values derived from Student ID ending in 43 (D1=4, D2=3)
// ============================================

var apiOrigin = window.location.origin;
if (!apiOrigin || apiOrigin === 'null' || apiOrigin.startsWith('file:') || apiOrigin.includes(':5500') || apiOrigin.includes(':3000')) {
    apiOrigin = 'http://localhost:5000';
}

var CONFIG = {
    // API base URL
    API_URL: apiOrigin + '/api',

    // LocalStorage keys
    TOKEN_KEY: 'token',
    USER_KEY: 'user',

    // Seeded constants (Student ID 43 -> D1=4, D2=3)
    MIN_USERNAME: 7,           // 6 + (D1 mod 3)
    MAX_USERNAME: 19,          // 16 + (D2 mod 5)
    MIN_PASSWORD: 11,          // 8 + (D2 mod 4)
    MAX_PASSWORD: 64,          // handout max
    MAX_NAME_FIELD: 23,        // 20 + D2
    FAILED_BEFORE_FORGOT: 2,   // 2 + (D1 mod 2)

    // Lockout tiers in seconds
    LOCKOUT_TIER1: 19,         // 15 + D1
    LOCKOUT_TIER2: 38,         // 30 + 2*D1
    LOCKOUT_TIER3: 76,         // 60 + 4*D1

    // OTP and session
    OTP_EXPIRY_MINUTES: 1,     // 1 minute OTP expiry
    IDLE_TIMEOUT_MINUTES: 9,   // 5 + (D1 mod 5)

    // IP blocking
    IP_BLOCK_THRESHOLD: 11,    // 8 + D2
    IP_BLOCK_SECONDS: 600      // 10 minutes
};

window.CONFIG = CONFIG;