from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class SearchResult(BaseModel):
    """Individual search result."""

    message_id: str
    conversation_id: str
    title: str
    provider: str
    role: str
    content: str
    timestamp: Optional[str] = None
    word_count: int
    relevance_score: float
    context: Optional[List[Dict[str, Any]]] = None


class SearchResponse(BaseModel):
    """Search API response."""

    query: str
    mode: str
    results: List[SearchResult]
    total: int
    execution_time_ms: int
    filters_applied: Dict[str, Any]


class SearchRequest(BaseModel):
    """Search request parameters."""

    query: str = Field(..., min_length=1, max_length=1000)
    mode: str = Field("hybrid", pattern="^(fts|vector|hybrid)$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)
    project_id: Optional[str] = None
    provider: Optional[str] = Field(None, pattern="^(chatgpt|claude)$")
    role: Optional[str] = Field(None, pattern="^(user|assistant|system)$")
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    threshold: float = Field(0.0, ge=0.0, le=1.0)
    include_context: bool = True


class ConversationSearchResult(BaseModel):
    """Conversation search result."""

    id: str
    title: str
    provider: str
    message_count: int
    word_count: int
    first_message_date: Optional[str] = None
    last_message_date: Optional[str] = None
    project_id: Optional[str] = None


class SearchStats(BaseModel):
    """Search statistics."""

    total_searches: int
    avg_execution_time_ms: float
    total_results: int
    unique_queries: int
    search_modes: List[Dict[str, int]]




