-- Add unique constraint for FAQ questions per chatbot
ALTER TABLE faqs
ADD CONSTRAINT unique_chatbot_question UNIQUE (chatbot_id, question);
