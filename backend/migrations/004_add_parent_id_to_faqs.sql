-- Add parent_id column to support hierarchical FAQs
ALTER TABLE faqs
ADD COLUMN parent_id INTEGER,
ADD CONSTRAINT fk_parent_faq FOREIGN KEY (parent_id) REFERENCES faqs(id) ON DELETE CASCADE;

-- Create index for faster parent lookups
CREATE INDEX idx_faq_parent_id ON faqs(parent_id);
