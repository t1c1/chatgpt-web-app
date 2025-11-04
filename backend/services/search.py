from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text, desc, asc
from sqlalchemy.orm import selectinload
from datetime import datetime
import re
import math
import structlog

from models.database import Message, Conversation, Embedding
from core.config import settings

logger = structlog.get_logger()


class SearchService:
    """Unified search service combining FTS, vector, and hybrid search."""

    def __init__(self, db_session: AsyncSession, user_id: str):
        self.db = db_session
        self.user_id = user_id

    async def full_text_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        **filters
    ) -> List[Dict[str, Any]]:
        """Full-text search using PostgreSQL FTS."""

        # Build base query
        base_query = select(Message).options(
            selectinload(Message.conversation)
        ).where(
            Message.user_id == self.user_id
        )

        # Apply filters
        if filters.get("project_id"):
            base_query = base_query.join(Conversation).where(
                Conversation.project_id == filters["project_id"]
            )

        if filters.get("provider"):
            if "conversation" not in str(base_query):
                base_query = base_query.join(Conversation)
            base_query = base_query.where(Conversation.provider == filters["provider"])

        if filters.get("role"):
            base_query = base_query.where(Message.role == filters["role"])

        if filters.get("date_from"):
            base_query = base_query.where(
                Message.timestamp_value >= filters["date_from"]
            )

        if filters.get("date_to"):
            base_query = base_query.where(
                Message.timestamp_value <= filters["date_to"]
            )

        # Apply FTS search using to_tsvector(content) @@ plainto_tsquery(query)
        ts_vector = func.to_tsvector('english', Message.content)
        ts_query = func.plainto_tsquery('english', query)

        base_query = base_query.where(ts_vector.op('@@')(ts_query))

        # Order by rank and limit
        rank = func.ts_rank(ts_vector, ts_query)
        base_query = base_query.order_by(desc(rank)).offset(offset).limit(limit)

        result = await self.db.execute(base_query)
        messages = result.scalars().all()

        return self._format_search_results(messages)

    async def vector_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        threshold: float = 0.0,
        **filters
    ) -> List[Dict[str, Any]]:
        """Vector similarity search using embeddings."""

        # TODO: Implement vector search using pgvector
        # This would require:
        # 1. Embedding model integration
        # 2. Query embedding generation
        # 3. Vector similarity search

        # For now, return empty results
        logger.warning("Vector search not yet implemented")
        return []

    async def hybrid_search(
        self,
        query: str,
        limit: int = 20,
        offset: int = 0,
        alpha: float = 0.5,
        threshold: float = 0.0,
        **filters
    ) -> List[Dict[str, Any]]:
        """Hybrid search combining FTS and vector search."""

        # Get FTS results
        fts_results = await self.full_text_search(
            query, limit=limit*2, offset=0, **filters
        )

        # Get vector results
        vector_results = await self.vector_search(
            query, limit=limit*2, offset=0, threshold=threshold, **filters
        )

        # Combine results using Reciprocal Rank Fusion (RRF)
        combined_results = self._combine_search_results(
            fts_results, vector_results, alpha, limit
        )

        return combined_results[offset:offset+limit]

    async def search_conversations(
        self,
        query: Optional[str] = None,
        project_id: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Search conversation metadata."""

        base_query = select(Conversation).where(
            Conversation.user_id == self.user_id
        )

        if project_id:
            base_query = base_query.where(Conversation.project_id == project_id)

        if provider:
            base_query = base_query.where(Conversation.provider == provider)

        if query:
            # Search in title
            search_query = func.plainto_tsquery('english', query)
            base_query = base_query.where(
                text("conversations.title_tsvector @@ :search_query")
            ).params(search_query=search_query)

        base_query = base_query.order_by(
            desc(Conversation.last_message_date)
        ).offset(offset).limit(limit)

        result = await self.db.execute(base_query)
        conversations = result.scalars().all()

        return [
            {
                "id": str(conv.id),
                "title": conv.title,
                "provider": conv.provider,
                "message_count": conv.message_count,
                "word_count": conv.word_count,
                "first_message_date": conv.first_message_date.isoformat() if conv.first_message_date else None,
                "last_message_date": conv.last_message_date.isoformat() if conv.last_message_date else None,
                "project_id": str(conv.project_id) if conv.project_id else None,
            }
            for conv in conversations
        ]

    async def add_conversation_context(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Add conversation context to search results."""

        if not results:
            return results

        # Get unique conversation IDs
        conv_ids = list({result["conversation_id"] for result in results})

        # Fetch conversation messages with context
        conv_query = select(Message).where(
            and_(
                Message.user_id == self.user_id,
                Message.conversation_id.in_(conv_ids)
            )
        ).order_by(Message.timestamp_value)

        result = await self.db.execute(conv_query)
        all_messages = result.scalars().all()

        # Group messages by conversation
        messages_by_conv = {}
        for msg in all_messages:
            conv_id = str(msg.conversation_id)
            if conv_id not in messages_by_conv:
                messages_by_conv[conv_id] = []
            messages_by_conv[conv_id].append({
                "id": str(msg.id),
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp_value.isoformat() if msg.timestamp_value else None,
                "is_current": False  # Will be set below
            })

        # Mark the current message in each conversation
        for result in results:
            conv_id = result["conversation_id"]
            if conv_id in messages_by_conv:
                current_msg_id = result["message_id"]
                for msg in messages_by_conv[conv_id]:
                    if msg["id"] == current_msg_id:
                        msg["is_current"] = True
                        break

                result["context"] = messages_by_conv[conv_id]

        return results

    def _format_search_results(self, messages: List[Message]) -> List[Dict[str, Any]]:
        """Format database messages into search results."""

        results = []
        for msg in messages:
            # Get conversation info
            conv = msg.conversation

            results.append({
                "message_id": str(msg.id),
                "conversation_id": str(msg.conversation_id),
                "title": conv.title if conv else "Untitled",
                "provider": conv.provider if conv else "unknown",
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp_value.isoformat() if msg.timestamp_value else None,
                "word_count": msg.word_count,
                "relevance_score": 1.0,  # TODO: Add actual relevance scoring
                "context": None,  # Will be filled by add_conversation_context
            })

        return results

    def _combine_search_results(
        self,
        fts_results: List[Dict[str, Any]],
        vector_results: List[Dict[str, Any]],
        alpha: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Combine FTS and vector results using weighted scoring."""

        # Create maps for quick lookup
        fts_map = {result["message_id"]: result for result in fts_results}
        vector_map = {result["message_id"]: result for result in vector_results}

        # Combine all unique results
        all_ids = set(fts_map.keys()) | set(vector_map.keys())
        combined_results = []

        for msg_id in all_ids:
            fts_result = fts_map.get(msg_id)
            vector_result = vector_map.get(msg_id)

            # Calculate combined score
            fts_score = fts_result.get("relevance_score", 0) if fts_result else 0
            vector_score = vector_result.get("relevance_score", 0) if vector_result else 0

            combined_score = alpha * vector_score + (1 - alpha) * fts_score

            # Use the more complete result as base
            base_result = fts_result or vector_result
            if base_result:
                base_result = base_result.copy()
                base_result["relevance_score"] = combined_score
                combined_results.append(base_result)

        # Sort by combined score and limit
        combined_results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return combined_results[:limit]

    async def get_message_by_id(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific message with conversation context."""

        result = await self.db.execute(
            select(Message).options(
                selectinload(Message.conversation)
            ).where(
                and_(
                    Message.id == message_id,
                    Message.user_id == self.user_id
                )
            )
        )

        message = result.scalar_one_or_none()
        if not message:
            return None

        return {
            "id": str(message.id),
            "conversation_id": str(message.conversation_id),
            "title": message.conversation.title if message.conversation else "Untitled",
            "provider": message.conversation.provider if message.conversation else "unknown",
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp_value.isoformat() if message.timestamp_value else None,
            "word_count": message.word_count,
        }




