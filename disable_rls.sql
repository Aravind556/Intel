-- Quick fix for RLS issues - Run this in Supabase SQL Editor

-- Temporarily disable RLS for testing (you can re-enable later)
ALTER TABLE users DISABLE ROW LEVEL SECURITY;
ALTER TABLE subjects DISABLE ROW LEVEL SECURITY; 
ALTER TABLE pdf_documents DISABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks DISABLE ROW LEVEL SECURITY;
ALTER TABLE processing_queue DISABLE ROW LEVEL SECURITY;

-- This will allow the app to work without authentication for now
