from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Mapped
from sqlalchemy.dialects.postgresql import UUID, JSONB

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    print("⚠️  pgvector not available - vector search features will be disabled")
    PGVECTOR_AVAILABLE = False
    # Create a dummy Vector class for compatibility
    class Vector:
        def __init__(self, dimension):
            self.dimension = dimension

Base = declarative_base()


class User(Base):
    """User model for authentication and multi-tenancy."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    search_logs = relationship("SearchLog", back_populates="user", cascade="all, delete-orphan")
    file_uploads = relationship("FileUpload", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """User session management."""

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")


class APIKey(Base):
    """API keys for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = Column(String(255), nullable=False)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    key_prefix = Column(String(20), unique=True, index=True, nullable=False)
    permissions = Column(JSONB, default=dict)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="api_keys")


class Project(Base):
    """Projects for organizing conversations."""

    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    settings = Column(JSONB, default=dict)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="projects")
    conversations = relationship("Conversation", back_populates="project", cascade="all, delete-orphan")


class Conversation(Base):
    """Conversation metadata and organization."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"))
    external_id = Column(String(255), index=True)  # ChatGPT/Claude conversation ID
    title = Column(String(500))
    provider = Column(String(50), nullable=False, index=True)  # 'chatgpt', 'claude'
    source_file = Column(String(255))  # Original export file name
    metadata_ = Column('metadata', JSONB, default=dict)  # Additional metadata from exports
    message_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    first_message_date = Column(DateTime(timezone=True))
    last_message_date = Column(DateTime(timezone=True))
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")
    project = relationship("Project", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    """Individual messages with full-text search."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    external_id = Column(String(255))  # Message ID from provider
    role = Column(String(50), nullable=False, index=True)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    word_count = Column(Integer, default=0)
    timestamp_value = Column(DateTime(timezone=True), index=True)
    metadata_ = Column('metadata', JSONB, default=dict)  # Message-specific metadata
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="messages")
    conversation = relationship("Conversation", back_populates="messages")
    embeddings = relationship("Embedding", back_populates="message", cascade="all, delete-orphan")


class Embedding(Base):
    """Vector embeddings for semantic search."""

    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    model_name = Column(String(100), nullable=False, index=True)
    # Only add vector column if pgvector is available
    if PGVECTOR_AVAILABLE:
        embedding_vector = Column(Vector(768))  # Adjust dimension based on model
    else:
        embedding_vector = Column(Text)  # Fallback to text storage
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    message = relationship("Message", back_populates="embeddings")


class SearchLog(Base):
    """Search analytics and usage tracking."""

    __tablename__ = "search_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    query_text = Column(Text, nullable=False)
    search_mode = Column(String(50), default="fts", index=True)  # 'fts', 'vector', 'hybrid'
    filters = Column(JSONB, default=dict)
    result_count = Column(Integer, default=0)
    execution_time_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="search_logs")


class FileUpload(Base):
    """File uploads tracking."""

    __tablename__ = "file_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)  # Changed to Integer for compatibility
    file_type = Column(String(50), nullable=False)  # 'chatgpt_export', 'claude_export'
    status = Column(String(50), default="processing", index=True)  # 'processing', 'completed', 'failed'
    error_message = Column(Text)
    processed_conversations = Column(Integer, default=0)
    processed_messages = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="file_uploads")


# Add relationships to User model
User.sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")




