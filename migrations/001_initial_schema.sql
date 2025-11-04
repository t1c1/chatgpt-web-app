-- ChatGPT Web App Database Schema
-- Migration 001: Initial schema with PostgreSQL + pgvector

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User sessions
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- API keys for programmatic access
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(20) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Projects/Collections - users can organize their conversations
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    settings JSONB DEFAULT '{}',
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Conversations table - normalized conversation data
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    external_id VARCHAR(255), -- ChatGPT/Claude conversation ID
    title VARCHAR(500),
    provider VARCHAR(50) NOT NULL, -- 'chatgpt', 'claude'
    source_file VARCHAR(255), -- Original export file name
    metadata JSONB DEFAULT '{}', -- Additional metadata from exports
    message_count INTEGER DEFAULT 0,
    word_count INTEGER DEFAULT 0,
    first_message_date TIMESTAMP WITH TIME ZONE,
    last_message_date TIMESTAMP WITH TIME ZONE,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Messages/Documents table - individual messages with full-text search
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    external_id VARCHAR(255), -- Message ID from provider
    role VARCHAR(50) NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    word_count INTEGER DEFAULT 0,
    timestamp_value TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}', -- Message-specific metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Vector embeddings for semantic search
CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID REFERENCES messages(id) ON DELETE CASCADE,
    model_name VARCHAR(100) NOT NULL,
    embedding_vector VECTOR(768), -- Adjust dimension based on model
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Search analytics and usage tracking
CREATE TABLE search_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    search_mode VARCHAR(50) DEFAULT 'fts', -- 'fts', 'vector', 'hybrid'
    filters JSONB DEFAULT '{}',
    result_count INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- File uploads tracking
CREATE TABLE file_uploads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_type VARCHAR(50) NOT NULL, -- 'chatgpt_export', 'claude_export'
    status VARCHAR(50) DEFAULT 'processing', -- 'processing', 'completed', 'failed'
    error_message TEXT,
    processed_conversations INTEGER DEFAULT 0,
    processed_messages INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_projects_user_id ON projects(user_id);
CREATE INDEX idx_conversations_user_id ON conversations(user_id);
CREATE INDEX idx_conversations_project_id ON conversations(project_id);
CREATE INDEX idx_conversations_provider ON conversations(provider);
CREATE INDEX idx_conversations_external_id ON conversations(external_id);
CREATE INDEX idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX idx_messages_user_id ON messages(user_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp_value);
CREATE INDEX idx_messages_role ON messages(role);
CREATE INDEX idx_embeddings_message_id ON embeddings(message_id);
CREATE INDEX idx_embeddings_model ON embeddings(model_name);
CREATE INDEX idx_search_logs_user_id ON search_logs(user_id);
CREATE INDEX idx_search_logs_created_at ON search_logs(created_at);
CREATE INDEX idx_file_uploads_user_id ON file_uploads(user_id);
CREATE INDEX idx_file_uploads_status ON file_uploads(status);

-- Full-text search indexes
CREATE INDEX idx_messages_content_fts ON messages USING GIN(to_tsvector('english', content));
CREATE INDEX idx_conversations_title_fts ON conversations USING GIN(to_tsvector('english', title));

-- Vector similarity index
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat(embedding_vector vector_cosine_ops);

-- Create default project for each user
CREATE OR REPLACE FUNCTION create_default_project_for_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO projects (user_id, name, description, is_default)
    VALUES (NEW.id, 'Default Project', 'Automatically created default project', TRUE);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to create default project
CREATE TRIGGER create_default_project_trigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION create_default_project_for_user();

-- Update conversation word count when messages are added
CREATE OR REPLACE FUNCTION update_conversation_stats()
RETURNS TRIGGER AS $$
BEGIN
    -- Update conversation message count and word count
    UPDATE conversations
    SET
        message_count = (
            SELECT COUNT(*) FROM messages WHERE conversation_id = COALESCE(NEW.conversation_id, OLD.conversation_id)
        ),
        word_count = (
            SELECT COALESCE(SUM(word_count), 0) FROM messages WHERE conversation_id = COALESCE(NEW.conversation_id, OLD.conversation_id)
        ),
        last_message_date = (
            SELECT MAX(timestamp_value) FROM messages WHERE conversation_id = COALESCE(NEW.conversation_id, OLD.conversation_id)
        ),
        first_message_date = (
            SELECT MIN(timestamp_value) FROM messages WHERE conversation_id = COALESCE(NEW.conversation_id, OLD.conversation_id)
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.conversation_id, OLD.conversation_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Triggers for conversation stats
CREATE TRIGGER update_conversation_stats_insert
    AFTER INSERT ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_stats();

CREATE TRIGGER update_conversation_stats_update
    AFTER UPDATE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_stats();

CREATE TRIGGER update_conversation_stats_delete
    AFTER DELETE ON messages
    FOR EACH ROW
    EXECUTE FUNCTION update_conversation_stats();

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Update timestamp triggers
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();




