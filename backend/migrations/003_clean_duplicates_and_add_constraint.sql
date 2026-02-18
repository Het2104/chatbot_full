-- Remove duplicate FAQs, keeping only the first one for each chatbot_id + question combination
DELETE FROM faqs
WHERE id NOT IN (
    SELECT MIN(id)
    FROM faqs
    GROUP BY chatbot_id, question
);

-- Add unique constraint for FAQ questions per chatbot
ALTER TABLE faqs
ADD CONSTRAINT unique_chatbot_question UNIQUE (chatbot_id, question);
