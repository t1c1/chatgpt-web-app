from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
import time
import uuid
from datetime import datetime

from core.database import get_db
from models.database import User, Message, Conversation, SearchLog
from schemas.search import SearchRequest, SearchResponse, SearchResult
from services.search import SearchService
from core.logging import get_logger

# TODO: Import auth dependencies when implemented
# from core.auth import get_current_user

router = APIRouter()
logger = get_logger()


# TODO: Add real authentication dependency
async def get_current_user(db: AsyncSession = Depends(get_db)):
    """Temporary placeholder for authentication dependency.
    Returns a default user for testing until auth is implemented.
    """
    from uuid import UUID
    
    # Prefer an existing sample user if present (created by sample data loader)
    sample_result = await db.execute(
        select(User).where(User.email == "sample@example.com")
    )
    user = sample_result.scalar_one_or_none()

    if user:
        return user

    # Fallback to a deterministic default user
    default_user_id = UUID("00000000-0000-0000-0000-000000000001")
    result = await db.execute(select(User).where(User.id == default_user_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=default_user_id,
            email="test@example.com",
            hashed_password="temp",
            full_name="Test User",
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info("Created default test user", user_id=str(user.id))

    return user


@router.get("/", response_model=SearchResponse)
async def search_conversations(
    query: str = Query(..., min_length=1, max_length=1000, description="Search query"),
    mode: str = Query("hybrid", pattern="^(fts|vector|hybrid)$", description="Search mode"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Results offset"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    provider: Optional[str] = Query(None, pattern="^(chatgpt|claude)$", description="Filter by provider"),
    role: Optional[str] = Query(None, pattern="^(user|assistant|system)$", description="Filter by message role"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    alpha: float = Query(0.5, ge=0.0, le=1.0, description="Vector weight in hybrid search"),
    threshold: float = Query(0.0, ge=0.0, le=1.0, description="Minimum similarity threshold"),
    include_context: bool = Query(True, description="Include conversation context"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = None,
):
    """
    Search conversations with advanced filtering and multiple search modes.

    - **fts**: Full-text search using PostgreSQL FTS
    - **vector**: Semantic search using embeddings
    - **hybrid**: Combines FTS and vector search
    """
    start_time = time.time()

    try:
        # Build filters
        filters = {
            "project_id": project_id,
            "provider": provider,
            "role": role,
            "date_from": date_from,
            "date_to": date_to,
        }

        # Initialize search service
        search_service = SearchService(db, current_user.id)

        # Perform search
        if mode == "fts":
            results = await search_service.full_text_search(
                query, limit=limit, offset=offset, **filters
            )
        elif mode == "vector":
            results = await search_service.vector_search(
                query, limit=limit, offset=offset, threshold=threshold, **filters
            )
        else:  # hybrid
            results = await search_service.hybrid_search(
                query, limit=limit, offset=offset, alpha=alpha,
                threshold=threshold, **filters
            )

        # Add context if requested
        if include_context and results:
            results = await search_service.add_conversation_context(results)

        execution_time = int((time.time() - start_time) * 1000)

        # Log search
        if background_tasks:
            background_tasks.add_task(
                log_search,
                user_id=current_user.id,
                query_text=query,
                search_mode=mode,
                filters=filters,
                result_count=len(results),
                execution_time_ms=execution_time,
                db=db
            )

        return SearchResponse(
            query=query,
            mode=mode,
            results=results,
            total=len(results),
            execution_time_ms=execution_time,
            filters_applied=filters
        )

    except Exception as e:
        logger.error("Search error", exc_info=e, query=query, mode=mode)
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/conversations", response_model=List[Dict[str, Any]])
async def search_conversation_list(
    query: Optional[str] = Query(None, description="Search conversation titles"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search conversation titles and metadata."""
    try:
        search_service = SearchService(db, current_user.id)

        results = await search_service.search_conversations(
            query=query,
            project_id=project_id,
            provider=provider,
            limit=limit,
            offset=offset
        )

        return results

    except Exception as e:
        logger.error("Conversation search error", exc_info=e)
        raise HTTPException(status_code=500, detail="Conversation search failed")


@router.get("/stats", response_model=Dict[str, Any])
async def get_search_stats(
    days: int = Query(30, ge=1, le=365, description="Days to look back"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get search statistics for the user."""
    try:
        cutoff_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

        # Get search statistics
        result = await db.execute(
            select(
                func.count(SearchLog.id).label("total_searches"),
                func.avg(SearchLog.execution_time_ms).label("avg_execution_time"),
                func.sum(SearchLog.result_count).label("total_results"),
                func.count(func.distinct(SearchLog.query_text)).label("unique_queries")
            ).where(
                and_(
                    SearchLog.user_id == current_user.id,
                    SearchLog.created_at >= cutoff_date
                )
            )
        )

        stats = result.first()

        # Get popular search modes
        mode_result = await db.execute(
            select(
                SearchLog.search_mode,
                func.count(SearchLog.id).label("count")
            ).where(
                and_(
                    SearchLog.user_id == current_user.id,
                    SearchLog.created_at >= cutoff_date
                )
            ).group_by(SearchLog.search_mode).order_by(func.count(SearchLog.id).desc())
        )

        mode_stats = mode_result.all()

        return {
            "total_searches": stats.total_searches or 0,
            "avg_execution_time_ms": float(stats.avg_execution_time or 0),
            "total_results": stats.total_results or 0,
            "unique_queries": stats.unique_queries or 0,
            "search_modes": [
                {"mode": mode, "count": count} for mode, count in mode_stats
            ]
        }

    except Exception as e:
        logger.error("Stats error", exc_info=e)
        raise HTTPException(status_code=500, detail="Failed to get search statistics")


async def log_search(
    user_id: str,
    query_text: str,
    search_mode: str,
    filters: dict,
    result_count: int,
    execution_time_ms: int,
    db: AsyncSession
):
    """Log search activity (background task)."""
    try:
        search_log = SearchLog(
            user_id=user_id,
            query_text=query_text,
            search_mode=search_mode,
            filters=filters,
            result_count=result_count,
            execution_time_ms=execution_time_ms
        )

        db.add(search_log)
        await db.commit()

    except Exception as e:
        logger.error("Failed to log search", exc_info=e)




