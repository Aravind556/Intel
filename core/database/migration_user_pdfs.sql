-- Migration: Add user-specific PDF ownership
-- This migration adds user_id to pdf_documents for direct user ownership

-- Add user_id column to pdf_documents table
ALTER TABLE pdf_documents 
ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;

-- Create index for fast user-based PDF lookups
CREATE INDEX idx_pdf_documents_user_id ON pdf_documents(user_id);

-- Create composite index for user + status queries
CREATE INDEX idx_pdf_documents_user_status ON pdf_documents(user_id, processing_status);

-- Update existing PDFs to have a user_id (assign to first user or create default user)
-- First, check if we have any users
DO $$
DECLARE
    default_user_id UUID;
    user_count INTEGER;
BEGIN
    -- Count existing users
    SELECT COUNT(*) INTO user_count FROM users;
    
    IF user_count = 0 THEN
        -- Create a default system user if no users exist
        INSERT INTO users (id, name, email, password_hash, role)
        VALUES (
            gen_random_uuid(),
            'System Admin',
            'admin@system.local',
            '$2b$12$LQv3c1yqBwEHxV4fXz0j.OJo0nCQ6YnP1nQr8dE3fL4qG5bH6cI7u', -- hash of 'admin123'
            'admin'
        )
        RETURNING id INTO default_user_id;
        
        RAISE NOTICE 'Created default system user with ID: %', default_user_id;
    ELSE
        -- Use the first existing user as default
        SELECT id INTO default_user_id FROM users ORDER BY created_at LIMIT 1;
        RAISE NOTICE 'Using existing user as default: %', default_user_id;
    END IF;
    
    -- Update all existing PDFs to belong to the default user
    UPDATE pdf_documents 
    SET user_id = default_user_id 
    WHERE user_id IS NULL;
    
    -- Log the number of PDFs updated
    RAISE NOTICE 'Updated % PDFs to belong to default user', (SELECT COUNT(*) FROM pdf_documents WHERE user_id = default_user_id);
END $$;

-- Make user_id NOT NULL after populating existing records
ALTER TABLE pdf_documents 
ALTER COLUMN user_id SET NOT NULL;

-- Update subjects table to ensure user ownership is consistent
-- (subjects already have user_id, but let's ensure PDFs match their subject's user)
UPDATE pdf_documents 
SET user_id = s.user_id 
FROM subjects s 
WHERE pdf_documents.subject_id = s.id 
AND pdf_documents.user_id != s.user_id;

-- Add a constraint to ensure PDF and subject belong to the same user
ALTER TABLE pdf_documents 
ADD CONSTRAINT chk_pdf_subject_same_user 
CHECK (
    subject_id IS NULL OR 
    user_id = (SELECT user_id FROM subjects WHERE id = subject_id)
);

-- Create a view for user PDF statistics
CREATE OR REPLACE VIEW user_pdf_stats AS
SELECT 
    u.id AS user_id,
    u.name AS user_name,
    u.email AS user_email,
    COUNT(p.id) AS total_pdfs,
    COUNT(CASE WHEN p.processing_status = 'completed' THEN 1 END) AS processed_pdfs,
    COUNT(CASE WHEN p.processing_status = 'pending' THEN 1 END) AS pending_pdfs,
    COUNT(CASE WHEN p.processing_status = 'failed' THEN 1 END) AS failed_pdfs,
    COALESCE(SUM(p.chunk_count), 0) AS total_chunks,
    COALESCE(SUM(p.file_size), 0) AS total_file_size,
    MAX(p.upload_date) AS last_upload_date
FROM users u
LEFT JOIN pdf_documents p ON u.id = p.user_id
GROUP BY u.id, u.name, u.email;

-- Grant permissions on the new view
GRANT SELECT ON user_pdf_stats TO authenticated;

-- Add helpful comments
COMMENT ON COLUMN pdf_documents.user_id IS 'Owner of this PDF document';
COMMENT ON INDEX idx_pdf_documents_user_id IS 'Fast lookup of PDFs by user';
COMMENT ON INDEX idx_pdf_documents_user_status IS 'Fast lookup of user PDFs by processing status';
COMMENT ON VIEW user_pdf_stats IS 'Summary statistics of PDF uploads per user';

-- Verify the migration
SELECT 
    'Migration completed successfully' AS status,
    COUNT(*) AS total_pdfs,
    COUNT(DISTINCT user_id) AS users_with_pdfs
FROM pdf_documents;
