from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import shutil
from pathlib import Path
import uuid
from datetime import datetime

from core.database import get_db
from core.config import settings
from models.database import User, FileUpload
from services.file_processor import FileProcessor
from core.logging import get_logger

logger = get_logger()

router = APIRouter()


async def get_current_user(db: AsyncSession = Depends(get_db)):
    """Temporary auth - returns default test user."""
    from sqlalchemy import select
    from uuid import UUID
    
    default_user_id = UUID("00000000-0000-0000-0000-000000000001")
    result = await db.execute(select(User).where(User.id == default_user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        user = User(
            id=default_user_id,
            email="test@example.com",
            hashed_password="temp",
            full_name="Test User",
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    return user


@router.post("/chatgpt")
async def upload_chatgpt_export(
    file: UploadFile = File(..., description="ChatGPT export file (JSON or ZIP)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload and process a ChatGPT export file.
    
    Accepts:
    - conversations.json
    - ZIP files containing ChatGPT exports
    """
    try:
        # Validate file type
        if not (file.filename.endswith('.json') or file.filename.endswith('.zip')):
            raise HTTPException(
                status_code=400,
                detail="Only .json and .zip files are supported"
            )
        
        # Create upload record
        upload_record = FileUpload(
            id=uuid.uuid4(),
            user_id=current_user.id,
            filename=file.filename,
            file_size_bytes=0,  # Will update after saving
            file_type="chatgpt_export",
            status="processing"
        )
        db.add(upload_record)
        await db.commit()
        
        # Save uploaded file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        file_path = upload_dir / f"{upload_record.id}_{file.filename}"
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update file size
        upload_record.file_size_bytes = file_path.stat().st_size
        await db.commit()
        
        logger.info(
            "File uploaded",
            filename=file.filename,
            size=upload_record.file_size_bytes,
            user_id=str(current_user.id)
        )
        
        # Process the file
        processor = FileProcessor(str(upload_dir), db)
        stats = await processor.process_chatgpt_export(file_path, str(current_user.id))
        
        # Update upload record
        upload_record.status = "completed" if not stats.get("errors") else "failed"
        upload_record.processed_conversations = stats.get("conversations_processed", 0)
        upload_record.processed_messages = stats.get("messages_processed", 0)
        upload_record.completed_at = datetime.utcnow()
        
        if stats.get("errors"):
            upload_record.error_message = "; ".join(stats["errors"])
        
        await db.commit()
        
        logger.info(
            "File processing complete",
            upload_id=str(upload_record.id),
            conversations=stats.get("conversations_processed"),
            messages=stats.get("messages_processed"),
            status=upload_record.status
        )
        
        return {
            "upload_id": str(upload_record.id),
            "status": upload_record.status,
            "filename": file.filename,
            "file_size": upload_record.file_size_bytes,
            "processing_stats": stats
        }
        
    except Exception as e:
        logger.error("Upload failed", exc_info=e, filename=file.filename)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/claude")
async def upload_claude_export(
    file: UploadFile = File(..., description="Claude export file (JSON or ZIP)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Upload and process a Claude export file.
    
    Accepts:
    - conversations.json from Claude exports
    - ZIP files containing Claude exports
    """
    try:
        # Validate file type
        if not (file.filename.endswith('.json') or file.filename.endswith('.zip')):
            raise HTTPException(
                status_code=400,
                detail="Only .json and .zip files are supported"
            )
        
        # Create upload record
        upload_record = FileUpload(
            id=uuid.uuid4(),
            user_id=current_user.id,
            filename=file.filename,
            file_size_bytes=0,
            file_type="claude_export",
            status="processing"
        )
        db.add(upload_record)
        await db.commit()
        
        # Save uploaded file
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(exist_ok=True, parents=True)
        
        file_path = upload_dir / f"{upload_record.id}_{file.filename}"
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update file size
        upload_record.file_size_bytes = file_path.stat().st_size
        await db.commit()
        
        logger.info(
            "File uploaded",
            filename=file.filename,
            size=upload_record.file_size_bytes,
            user_id=str(current_user.id)
        )
        
        # Process the file
        processor = FileProcessor(str(upload_dir), db)
        stats = await processor.process_claude_export(file_path, str(current_user.id))
        
        # Update upload record
        upload_record.status = "completed" if not stats.get("errors") else "failed"
        upload_record.processed_conversations = stats.get("conversations_processed", 0)
        upload_record.processed_messages = stats.get("messages_processed", 0)
        upload_record.completed_at = datetime.utcnow()
        
        if stats.get("errors"):
            upload_record.error_message = "; ".join(stats["errors"])
        
        await db.commit()
        
        logger.info(
            "File processing complete",
            upload_id=str(upload_record.id),
            conversations=stats.get("conversations_processed"),
            messages=stats.get("messages_processed"),
            status=upload_record.status
        )
        
        return {
            "upload_id": str(upload_record.id),
            "status": upload_record.status,
            "filename": file.filename,
            "file_size": upload_record.file_size_bytes,
            "processing_stats": stats
        }
        
    except Exception as e:
        logger.error("Upload failed", exc_info=e, filename=file.filename)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the status of a file upload."""
    from sqlalchemy import select
    from uuid import UUID
    
    try:
        upload_uuid = UUID(upload_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")
    
    result = await db.execute(
        select(FileUpload).where(
            FileUpload.id == upload_uuid,
            FileUpload.user_id == current_user.id
        )
    )
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    return {
        "upload_id": str(upload.id),
        "filename": upload.filename,
        "status": upload.status,
        "file_type": upload.file_type,
        "file_size": upload.file_size_bytes,
        "processed_conversations": upload.processed_conversations,
        "processed_messages": upload.processed_messages,
        "error_message": upload.error_message,
        "created_at": upload.created_at.isoformat() if upload.created_at else None,
        "completed_at": upload.completed_at.isoformat() if upload.completed_at else None,
    }


@router.get("/history")
async def get_upload_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get upload history for the current user."""
    from sqlalchemy import select, desc
    
    result = await db.execute(
        select(FileUpload)
        .where(FileUpload.user_id == current_user.id)
        .order_by(desc(FileUpload.created_at))
        .limit(limit)
    )
    uploads = result.scalars().all()
    
    return [
        {
            "upload_id": str(upload.id),
            "filename": upload.filename,
            "status": upload.status,
            "file_type": upload.file_type,
            "processed_conversations": upload.processed_conversations,
            "processed_messages": upload.processed_messages,
            "created_at": upload.created_at.isoformat() if upload.created_at else None,
        }
        for upload in uploads
    ]

