-- Migration 008: Create users table for authentication
-- Adds user authentication and role-based authorization support

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for faster lookups
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

-- Add comments
COMMENT ON TABLE users IS 'User accounts for authentication and authorization';
COMMENT ON COLUMN users.email IS 'User email address (unique, used for login)';
COMMENT ON COLUMN users.username IS 'User display name (unique)';
COMMENT ON COLUMN users.password_hash IS 'Bcrypt hashed password';
COMMENT ON COLUMN users.role IS 'User role: "user" or "admin"';
COMMENT ON COLUMN users.is_active IS 'Whether user account is active';

-- Add user_id foreign key to chatbots table for ownership
ALTER TABLE chatbots 
ADD COLUMN user_id INTEGER REFERENCES users(id);

-- Add user_id foreign key to chat_sessions table for ownership
ALTER TABLE chat_sessions 
ADD COLUMN user_id INTEGER REFERENCES users(id);

-- Add indexes for foreign keys
CREATE INDEX idx_chatbots_user_id ON chatbots(user_id);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);

-- Comments for ownership columns
COMMENT ON COLUMN chatbots.user_id IS 'Owner of the chatbot (references users table)';
COMMENT ON COLUMN chat_sessions.user_id IS 'User who owns the chat session (references users table)';
