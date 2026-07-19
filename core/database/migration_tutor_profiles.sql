-- AI Tutor - Student Profiles & Mastery Tracking Migrations
-- Configures student tracking tables in Supabase

-- 1. Student Profiles Table
CREATE TABLE IF NOT EXISTS student_profiles (
    id UUID REFERENCES users(id) ON DELETE CASCADE PRIMARY KEY,
    learning_preferences JSONB DEFAULT '{
        "analogy_style": "practical",
        "explanation_depth": "medium",
        "coding_language": "python"
    }'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for student profiles
ALTER TABLE student_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own profile state" ON student_profiles
FOR ALL USING (auth.uid() = id);

-- 2. Lesson Progress & Mastery Tracking
CREATE TABLE IF NOT EXISTS student_topic_mastery (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    concept_name VARCHAR(255) NOT NULL,
    mastery_score FLOAT DEFAULT 0.0 CHECK (mastery_score >= 0.0 AND mastery_score <= 1.0),
    times_tested INTEGER DEFAULT 0,
    last_tested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(student_id, concept_name)
);

-- Enable RLS for topic mastery
ALTER TABLE student_topic_mastery ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own topic mastery" ON student_topic_mastery
FOR SELECT USING (auth.uid() = student_id);

-- 3. Quiz and Evaluation History
CREATE TABLE IF NOT EXISTS student_assessment_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    concept_name VARCHAR(255) NOT NULL,
    question_text TEXT NOT NULL,
    student_answer TEXT,
    is_correct BOOLEAN NOT NULL,
    score FLOAT CHECK (score >= 0.0 AND score <= 1.0),
    misconceptions_detected JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for assessment history
ALTER TABLE student_assessment_history ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own assessment history" ON student_assessment_history
FOR SELECT USING (auth.uid() = student_id);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_student_topic_mastery_student ON student_topic_mastery(student_id);
CREATE INDEX IF NOT EXISTS idx_student_topic_mastery_concept ON student_topic_mastery(concept_name);
CREATE INDEX IF NOT EXISTS idx_student_assessment_history_student ON student_assessment_history(student_id);

-- 4. Search across all user documents (RPC vector search function)
CREATE OR REPLACE FUNCTION match_all_documents (
    query_embedding VECTOR(768),
    user_id UUID,
    match_threshold FLOAT DEFAULT 0.5,
    match_count INT DEFAULT 10
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    metadata JSONB,
    similarity FLOAT,
    pdf_title VARCHAR(255),
    page_number INTEGER,
    chunk_index INTEGER
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
        dc.chunk_index
    FROM document_chunks dc
    JOIN pdf_documents pd ON dc.pdf_id = pd.id
    WHERE pd.user_id = match_all_documents.user_id
    AND pd.processed = TRUE
    AND dc.embedding IS NOT NULL
    AND 1 - (dc.embedding <=> query_embedding) > match_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT match_count;
$$;

-- Grant necessary permissions
GRANT ALL ON student_profiles TO authenticated;
GRANT ALL ON student_topic_mastery TO authenticated;
GRANT ALL ON student_assessment_history TO authenticated;
