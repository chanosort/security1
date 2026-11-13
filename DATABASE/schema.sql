-- ── ADDED for handout §4, §5, §6, §8, §13 ──
-- Run with: psql -U postgres -d e_tracker_db -f schema.sql

CREATE SCHEMA IF NOT EXISTS e_tracker;
SET search_path TO e_tracker;

-- Users (rewritten to meet §4 core + system fields)
CREATE TABLE IF NOT EXISTS users (
  user_id         SERIAL PRIMARY KEY,
  id_number       VARCHAR(9)  UNIQUE NOT NULL,           -- xxxx-xxxx, PK per §4.4 (unique surrogate kept for FK stability)
  first_name      VARCHAR(23) NOT NULL,
  middle_name     VARCHAR(23),
  family_name     VARCHAR(23) NOT NULL,
  name_extension  VARCHAR(10),
  birthdate       DATE        NOT NULL,
  age             INT         NOT NULL,
  purok           VARCHAR(50) NOT NULL,
  barangay        VARCHAR(50) NOT NULL,
  municipality    VARCHAR(50) NOT NULL,
  province        VARCHAR(50) NOT NULL,
  region          VARCHAR(50) NOT NULL,
  postal_code     VARCHAR(10) NOT NULL,
  email           VARCHAR(100) UNIQUE NOT NULL,
  username        VARCHAR(19) UNIQUE NOT NULL,
  password_hash   VARCHAR(255) NOT NULL,
  role            VARCHAR(16) DEFAULT 'user',            -- admin | user
  -- System fields (financial — cooperative)
  tin_number_enc  TEXT,                                  -- encrypted (Protection 13)
  income_bracket  VARCHAR(20),
  date_joined     DATE,
  loan_purpose    VARCHAR(100),
  currency        VARCHAR(8) DEFAULT 'PHP',
  monthly_budget  NUMERIC(14,2) DEFAULT 0,
  -- Privacy consent
  consent_at      TIMESTAMPTZ,
  -- Account state
  verified        BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Security questions (answers hashed, lowercase)
CREATE TABLE IF NOT EXISTS security_questions (
  sq_id       SERIAL PRIMARY KEY,
  user_id     INT REFERENCES users(user_id) ON DELETE CASCADE,
  question_code VARCHAR(4) NOT NULL,          -- Q1, Q4, Q7
  question_text TEXT NOT NULL,
  answer_hash VARCHAR(255) NOT NULL
);

-- OTPs
CREATE TABLE IF NOT EXISTS otps (
  otp_id    SERIAL PRIMARY KEY,
  user_id   INT REFERENCES users(user_id) ON DELETE CASCADE,
  purpose   VARCHAR(16) NOT NULL,             -- register | login | reset
  code_hash VARCHAR(255) NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  attempts  INT DEFAULT 0,
  consumed  BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Password history (Protection 7)
CREATE TABLE IF NOT EXISTS password_history (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES users(user_id) ON DELETE CASCADE,
  password_hash VARCHAR(255) NOT NULL,
  changed_at TIMESTAMPTZ DEFAULT now()
);

-- Activity log (append-only)
CREATE TABLE IF NOT EXISTS activity_log (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(40) NOT NULL,
  username_type VARCHAR(16),
  user_id INT,
  ip_address INET,
  user_agent TEXT,
  details TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Security flags (written by monitoring script)
CREATE TABLE IF NOT EXISTS security_flags (
  id SERIAL PRIMARY KEY,
  pattern VARCHAR(40) NOT NULL,
  target VARCHAR(120) NOT NULL,
  severity VARCHAR(8) NOT NULL,
  details TEXT,
  day DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (pattern, target, day)
);

-- IP blocks
CREATE TABLE IF NOT EXISTS ip_blocks (
  ip_address INET PRIMARY KEY,
  blocked_until TIMESTAMPTZ NOT NULL,
  reason TEXT
);

-- Categories
CREATE TABLE IF NOT EXISTS categories (
  category_id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  category_name VARCHAR(100) NOT NULL,
  category_type VARCHAR(20) NOT NULL CHECK (category_type IN ('Income', 'Expense')),
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uk_category_user_name UNIQUE (user_id, category_name)
);

-- Transactions (including future bills & status)
CREATE TABLE IF NOT EXISTS transactions (
  transaction_id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  category_id INT REFERENCES categories(category_id) ON DELETE CASCADE,
  transaction_type VARCHAR(20) NOT NULL CHECK (transaction_type IN ('Income', 'Expense')),
  amount NUMERIC(14,2) NOT NULL CHECK (amount > 0),
  description VARCHAR(255),
  transaction_date DATE NOT NULL DEFAULT CURRENT_DATE,
  status VARCHAR(20) NOT NULL DEFAULT 'Completed',
  recurrence VARCHAR(20) NOT NULL DEFAULT 'One-time',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Budgets
CREATE TABLE IF NOT EXISTS budgets (
  budget_id SERIAL PRIMARY KEY,
  user_id INT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  category_id INT NOT NULL REFERENCES categories(category_id) ON DELETE CASCADE,
  amount NUMERIC(14,2) NOT NULL CHECK (amount >= 0),
  month INT NOT NULL CHECK (month BETWEEN 1 AND 12),
  year INT NOT NULL CHECK (year >= 2000 AND year <= 2100),
  created_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT uk_budget_user_category_month_year UNIQUE (user_id, category_id, month, year)
);

-- ── Seed admin (never through registration form) ──
-- After running schema, create the admin manually:
-- INSERT INTO users (id_number, first_name, family_name, birthdate, age, purok, barangay,
--   municipality, province, region, postal_code, email, username, password_hash, role, verified)
-- VALUES ('0000-0001','Admin','User','1990-01-01',35,'Purok 1','Barangay 1','City','Province','Region','1000',
--   'admin@example.com','adminuser','<bcrypt_hash>','admin',TRUE);