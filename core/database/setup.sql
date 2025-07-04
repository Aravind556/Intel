-- AI Tutor Backend - PDF Storage & Vector Database Setup
-- Supabase + pgvector configuration for LLM data retrieval

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- User Management (Basic for PDF ownership)
CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    role VARCHAR(50) DEFAULT 'student',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Subject Management (Categorize PDFs by subject)
CREATE TABLE subjects (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3B82F6', -- For UI display
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, name) -- Prevent duplicate subject names per user
);

-- PDF Document Storage
CREATE TABLE pdf_documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    filename VARCHAR(255) NOT NULL, -- Stored filename
    original_filename VARCHAR(255) NOT NULL, -- User's original filename
    subject_id UUID REFERENCES subjects(id) ON DELETE CASCADE,
    file_path TEXT, -- Path in Supabase storage
    file_size BIGINT NOT NULL,
    total_pages INTEGER,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE,
    processing_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'processing', 'completed', 'failed'
    processing_error TEXT, -- Store error details if processing fails
    metadata JSONB, -- Additional PDF metadata (author, creation date, etc.)
    chunk_count INTEGER DEFAULT 0 -- Track how many chunks were created
);

-- Document Chunks with Vector Embeddings (Core for LLM retrieval)
CREATE TABLE document_chunks (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pdf_id UUID REFERENCES pdf_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL, -- Actual text content
    chunk_index INTEGER NOT NULL, -- Order within the document
    page_number INTEGER, -- Which page this chunk came from
    embedding VECTOR(768), -- Ollama nomic-embed-text model (768 dimensions)
    token_count INTEGER, -- Number of tokens in this chunk
    metadata JSONB, -- Additional context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Ensure unique ordering within each PDF
    UNIQUE(pdf_id, chunk_index)
);

-- Chunk metadata structure:
COMMENT ON COLUMN document_chunks.metadata IS 
'JSON structure: {
    "subject": "Mathematics",
    "topic": "Calculus", 
    "section": "Derivatives",
    "difficulty_level": 2,
    "chunk_type": "definition|example|explanation|formula|theorem",
    "keywords": ["derivative", "limit", "function"],
    "page_start": 15,
    "page_end": 16
}';

-- PDF Processing Queue (Track processing status)
CREATE TABLE processing_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    pdf_id UUID REFERENCES pdf_documents(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'queued', -- 'queued', 'processing', 'completed', 'failed'
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for optimal performance
-- Vector similarity search index (most important for LLM retrieval)
CREATE INDEX idx_document_chunks_embedding 
ON document_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);

-- Indexes for fast PDF and subject lookups
CREATE INDEX idx_pdf_documents_subject_id ON pdf_documents(subject_id);
CREATE INDEX idx_pdf_documents_processed ON pdf_documents(processed, processing_status);
CREATE INDEX idx_document_chunks_pdf_id ON document_chunks(pdf_id);
CREATE INDEX idx_document_chunks_page ON document_chunks(page_number);
CREATE INDEX idx_subjects_user_id ON subjects(user_id);
CREATE INDEX idx_processing_queue_status ON processing_queue(status);

-- Full-text search index for content (backup search method)
CREATE INDEX idx_document_chunks_content_fts 
ON document_chunks 
USING gin(to_tsvector('english', content));

-- Vector search function for LLM retrieval
CREATE OR REPLACE FUNCTION match_documents_by_subject (
    query_embedding VECTOR(384),
    subject_name VARCHAR(255),
    user_id UUID,
    match_threshold FLOAT DEFAULT 0.75,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    pdf_title VARCHAR(255),
    page_number INTEGER,
    subject_name_result VARCHAR(255)
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        dc.id as chunk_id,
        dc.content,
        dc.metadata,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        pd.original_filename as pdf_title,
        dc.page_number,
        s.name as subject_name_result
    FROM document_chunks dc
    JOIN pdf_documents pd ON dc.pdf_id = pd.id
    JOIN subjects s ON pd.subject_id = s.id
    WHERE s.name ILIKE subject_name -- Case-insensitive subject matching
    AND s.user_id = user_id
    AND pd.processed = TRUE -- Only search processed documents
    AND dc.embedding IS NOT NULL -- Ensure embedding exists
    AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Function to get all available subjects for a user
CREATE OR REPLACE FUNCTION get_user_subjects(user_id UUID)
RETURNS TABLE (
    subject_id UUID,
    subject_name VARCHAR(255),
    pdf_count BIGINT,
    total_chunks BIGINT,
    last_upload TIMESTAMP WITH TIME ZONE
)
LANGUAGE SQL STABLE
AS $$
    SELECT 
        s.id as subject_id,
        s.name as subject_name,
        COUNT(pd.id) as pdf_count,
        COALESCE(SUM(pd.chunk_count), 0) as total_chunks,
        MAX(pd.upload_date) as last_upload
    FROM subjects s
    LEFT JOIN pdf_documents pd ON s.id = pd.subject_id AND pd.processed = TRUE
    WHERE s.user_id = user_id
    GROUP BY s.id, s.name
    ORDER BY s.name;
$$;

-- Function to search within a specific PDF
CREATE OR REPLACE FUNCTION search_within_pdf (
    query_embedding VECTOR(384),
    pdf_document_id UUID,
    match_threshold FLOAT DEFAULT 0.75,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    page_number INTEGER,
    similarity FLOAT,
    chunk_index INTEGER
)
LANGUAGE SQL STABLE
AS $$
    SELECT
        dc.id as chunk_id,
        dc.content,
        dc.page_number,
        1 - (dc.embedding <=> query_embedding) AS similarity,
        dc.chunk_index
    FROM document_chunks dc
    WHERE dc.pdf_id = pdf_document_id
    AND dc.embedding IS NOT NULL
    AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Function to get PDF processing statistics
CREATE OR REPLACE FUNCTION get_processing_stats()
RETURNS TABLE (
    total_pdfs BIGINT,
    processed_pdfs BIGINT,
    processing_pdfs BIGINT,
    failed_pdfs BIGINT,
    total_chunks BIGINT,
    avg_chunks_per_pdf NUMERIC
)
LANGUAGE SQL STABLE
AS $$
    SELECT 
        COUNT(*) as total_pdfs,
        COUNT(*) FILTER (WHERE processed = TRUE) as processed_pdfs,
        COUNT(*) FILTER (WHERE processing_status = 'processing') as processing_pdfs,
        COUNT(*) FILTER (WHERE processing_status = 'failed') as failed_pdfs,
        COALESCE(SUM(chunk_count), 0) as total_chunks,
        CASE 
            WHEN COUNT(*) FILTER (WHERE processed = TRUE) > 0 
            THEN ROUND(SUM(chunk_count)::NUMERIC / COUNT(*) FILTER (WHERE processed = TRUE), 2)
            ELSE 0 
        END as avg_chunks_per_pdf
    FROM pdf_documents;
$$;

-- Row Level Security (RLS) for data isolation
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdf_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_queue ENABLE ROW LEVEL SECURITY;

-- RLS Policies
-- Users can only see their own data
CREATE POLICY "Users can view own profile" ON users 
FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON users 
FOR UPDATE USING (auth.uid() = id);

-- Users can only access their own subjects
CREATE POLICY "Users can manage own subjects" ON subjects 
FOR ALL USING (auth.uid() = user_id);

-- Users can only access PDFs in their subjects
CREATE POLICY "Users can access own PDFs" ON pdf_documents 
FOR ALL USING (
    EXISTS (
        SELECT 1 FROM subjects 
        WHERE subjects.id = pdf_documents.subject_id 
        AND subjects.user_id = auth.uid()
    )
);

-- Users can only access chunks from their PDFs
CREATE POLICY "Users can access own document chunks" ON document_chunks 
FOR ALL USING (
    EXISTS (
        SELECT 1 FROM pdf_documents pd
        JOIN subjects s ON pd.subject_id = s.id
        WHERE pd.id = document_chunks.pdf_id 
        AND s.user_id = auth.uid()
    )
);

-- Processing queue access
CREATE POLICY "Users can view own processing jobs" ON processing_queue 
FOR ALL USING (
    EXISTS (
        SELECT 1 FROM pdf_documents pd
        JOIN subjects s ON pd.subject_id = s.id
        WHERE pd.id = processing_queue.pdf_id 
        AND s.user_id = auth.uid()
    )
);

-- Insert some sample data for testing (optional)
-- Uncomment below if you want test data

/*
-- Sample user
INSERT INTO users (id, name, email, role) VALUES 
('550e8400-e29b-41d4-a716-446655440000', 'Test Student', 'student@test.com', 'student');

-- Sample subjects
INSERT INTO subjects (id, name, user_id, description) VALUES 
('550e8400-e29b-41d4-a716-446655440001', 'Mathematics', '550e8400-e29b-41d4-a716-446655440000', 'Calculus and Algebra'),
('550e8400-e29b-41d4-a716-446655440002', 'Physics', '550e8400-e29b-41d4-a716-446655440000', 'Mechanics and Thermodynamics');
*/

-- View to easily see PDF processing status
CREATE VIEW pdf_processing_overview AS
SELECT 
    pd.id,
    pd.original_filename,
    s.name as subject_name,
    u.name as user_name,
    pd.file_size,
    pd.total_pages,
    pd.chunk_count,
    pd.processing_status,
    pd.upload_date,
    CASE 
        WHEN pd.processed = TRUE THEN 'Ready for LLM'
        WHEN pd.processing_status = 'processing' THEN 'Being Processed'
        WHEN pd.processing_status = 'failed' THEN 'Failed - ' || COALESCE(pd.processing_error, 'Unknown error')
        ELSE 'Waiting to Process'
    END as status_description
FROM pdf_documents pd
JOIN subjects s ON pd.subject_id = s.id
JOIN users u ON s.user_id = u.id
ORDER BY pd.upload_date DESC;

-- Grant necessary permissions for the application to work
-- Note: In production, create specific service roles with minimal required permissions

COMMENT ON TABLE pdf_documents IS 'Stores metadata about uploaded PDF files';
COMMENT ON TABLE document_chunks IS 'Stores text chunks with vector embeddings for LLM retrieval';
COMMENT ON TABLE subjects IS 'Organizes PDFs by academic subjects';
COMMENT ON INDEX idx_document_chunks_embedding IS 'Vector similarity search index - critical for LLM performance';

-- Complete! Database is ready for PDF storage and LLM data retrieval
