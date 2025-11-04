#!/usr/bin/env python3
"""
Sample data loader for ChatGPT Web App.
Loads sample conversations from the data directory into the PostgreSQL database.
"""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models.database import Base, User, Conversation, Message
from core.config import settings


async def load_sample_data():
    """Load sample data into the database."""
    print("🚀 Loading sample data into ChatGPT Web App...")

    # Create database engine using Docker container connection
    database_url = (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    engine = create_async_engine(
        database_url,
        echo=True,
        future=True,
    )

    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Sample data paths
    data_dir = Path(__file__).parent.parent.parent / "data"
    openai_file = data_dir / "openai" / "conversations.json"
    anthropic_file = data_dir / "anthropic" / "conversations.json"

    # Create a sample user
    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(
            "SELECT id FROM users WHERE email = :email",
            {"email": "sample@example.com"}
        )
        user = result.fetchone()

        if not user:
            user = User(
                id=uuid.uuid4(),
                email="sample@example.com",
                hashed_password="sample",  # In real app, this would be hashed
                full_name="Sample User",
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✅ Created sample user: {user.id}")
        else:
            user = await session.get(User, user.id)
            print(f"✅ Found existing sample user: {user.id}")

    # Load ChatGPT data
    if openai_file.exists():
        await load_chatgpt_data(async_session, user.id, openai_file)

    # Load Claude data
    if anthropic_file.exists():
        await load_claude_data(async_session, user.id, anthropic_file)

    print("🎉 Sample data loading complete!")


async def load_chatgpt_data(sessionmaker, user_id: uuid.UUID, file_path: Path):
    """Load ChatGPT conversations from JSON file."""
    print(f"📁 Loading ChatGPT data from {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load ChatGPT data: {e}")
        return

    async with sessionmaker() as session:
        for item in data:
            # Create conversation
            conversation = Conversation(
                id=uuid.uuid4(),
                user_id=user_id,
                external_id=item.get("id", ""),
                title=item.get("title", "Untitled Conversation"),
                provider="chatgpt",
                source_file="conversations.json",
                metadata_=item.get("metadata", {}),
                message_count=len(item.get("messages", [])),
                created_at=datetime.now(),
            )
            session.add(conversation)

            # Create messages
            for msg in item.get("messages", []):
                message = Message(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    conversation_id=conversation.id,
                    external_id=msg.get("id", ""),
                    role=msg.get("role", "unknown"),
                    content=msg.get("content", ""),
                    word_count=len(msg.get("content", "").split()) if msg.get("content") else 0,
                    timestamp_value=datetime.now(),  # ChatGPT doesn't always have timestamps
                    metadata_=msg.get("metadata", {}),
                    created_at=datetime.now(),
                )
                session.add(message)

        await session.commit()
        print(f"✅ Loaded {len(data)} ChatGPT conversations")


async def load_claude_data(sessionmaker, user_id: uuid.UUID, file_path: Path):
    """Load Claude conversations from JSON file."""
    print(f"📁 Loading Claude data from {file_path}...")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load Claude data: {e}")
        return

    async with sessionmaker() as session:
        for item in data:
            # Create conversation
            conversation = Conversation(
                id=uuid.uuid4(),
                user_id=user_id,
                external_id=item.get("id", ""),
                title=item.get("title", "Untitled Conversation"),
                provider="claude",
                source_file="conversations.json",
                metadata_=item.get("metadata", {}),
                message_count=len(item.get("messages", [])),
                created_at=datetime.now(),
            )
            session.add(conversation)

            # Create messages
            for msg in item.get("messages", []):
                message = Message(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    conversation_id=conversation.id,
                    external_id=msg.get("id", ""),
                    role=msg.get("role", "unknown"),
                    content=msg.get("content", ""),
                    word_count=len(msg.get("content", "").split()) if msg.get("content") else 0,
                    timestamp_value=datetime.now(),
                    metadata_=msg.get("metadata", {}),
                    created_at=datetime.now(),
                )
                session.add(message)

        await session.commit()
        print(f"✅ Loaded {len(data)} Claude conversations")


if __name__ == "__main__":
    asyncio.run(load_sample_data())
