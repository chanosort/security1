CREATE SCHEMA IF NOT EXISTS e_tracker;

DROP TABLE IF EXISTS budgets CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS users CASCADE;


CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    monthly_budget NUMERIC(12,2) DEFAULT 0 CHECK (monthly_budget >= 0),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE categories (
    category_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    category_name VARCHAR(50) NOT NULL,
    category_type VARCHAR(20) NOT NULL
        CHECK (category_type IN ('Income', 'Expense')),
    
    -- Foreign key to users table
    CONSTRAINT fk_category_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,
    
    -- Prevent duplicate category names per user
    CONSTRAINT uk_category_user_name 
        UNIQUE (user_id, category_name)
);

CREATE TABLE transactions (
    transaction_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    transaction_type VARCHAR(20) NOT NULL
        CHECK (transaction_type IN ('Income', 'Expense')),
    amount NUMERIC(12,2) NOT NULL
        CHECK (amount > 0),
    description VARCHAR(255),
    transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key to users table
    CONSTRAINT fk_transaction_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    -- Foreign key to categories table
    CONSTRAINT fk_transaction_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON DELETE RESTRICT  -- Prevents deleting categories with transactions
);


CREATE TABLE budgets (
    budget_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    amount NUMERIC(12,2) NOT NULL
        CHECK (amount >= 0),
    month INT NOT NULL
        CHECK (month BETWEEN 1 AND 12),
    year INT NOT NULL
        CHECK (year >= 2000 AND year <= 2100),

    -- Foreign key to users table
    CONSTRAINT fk_budget_user
        FOREIGN KEY (user_id)
        REFERENCES users(user_id)
        ON DELETE CASCADE,

    -- Foreign key to categories table
    CONSTRAINT fk_budget_category
        FOREIGN KEY (category_id)
        REFERENCES categories(category_id)
        ON DELETE CASCADE,
    
    -- Prevent duplicate budgets per user/category/month/year
    CONSTRAINT uk_budget_user_category_month_year 
        UNIQUE (user_id, category_id, month, year)
);

-- INDEXES (for better performance)
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_date);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_categories_user ON categories(user_id);
CREATE INDEX idx_budgets_user_month ON budgets(user_id, month, year);
CREATE INDEX idx_budgets_category ON budgets(category_id);

-- ============================================
-- VERIFY TABLES (Optional - just for confirmation)
-- ============================================
-- SELECT schemaname, tablename 
-- FROM pg_tables 
-- WHERE schemaname = 'e_tracker'
-- ORDER BY tablename;

-- ============================================
-- GRANT PERMISSIONS (if needed)
-- ============================================
-- GRANT ALL PRIVILEGES ON SCHEMA e_tracker TO postgres;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA e_tracker TO postgres;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA e_tracker TO postgres;