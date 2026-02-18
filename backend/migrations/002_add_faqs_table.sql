BEGIN;

-- Create FAQs table
CREATE TABLE IF NOT EXISTS faqs (
    id SERIAL PRIMARY KEY,
    chatbot_id INTEGER NOT NULL REFERENCES chatbots(id) ON DELETE CASCADE,
    question VARCHAR NOT NULL,
    answer TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_faqs_chatbot_id ON faqs(chatbot_id);
CREATE INDEX IF NOT EXISTS idx_faqs_is_active ON faqs(is_active);

COMMIT;
