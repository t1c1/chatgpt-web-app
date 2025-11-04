#!/usr/bin/env python3
"""
Load ChatGPT (OpenAI) exports into the ChatGPT Web App database.

Usage:
  python3 scripts/load_from_export.py --path "/absolute/path/to/20251103-OpenAI-Export"

Notes:
  - Data is associated with the default test user used by the API
    (UUID 00000000-0000-0000-0000-000000000001) so searches work immediately.
  - Supports a folder containing conversations.json or a direct path to the file.
"""

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List

# Add backend to sys.path for imports
SCRIPT_DIR = Path(__file__).parent
BACKEND_DIR = SCRIPT_DIR.parent / "backend"
sys.path.append(str(BACKEND_DIR))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from models.database import Base, User, Conversation, Message


DEFAULT_TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def find_conversations_json(export_path: Path) -> Path:
    if export_path.is_file():
        return export_path
    # Common file name in OpenAI exports
    candidate = export_path / "conversations.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Could not find conversations.json in {export_path}")


def normalize_chatgpt(data: Any) -> Iterable[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        convs = data.get("conversations")
        if isinstance(convs, list):
            return convs
    return []


def extract_message_content(msg: dict) -> str:
    content = msg.get("content") or msg.get("text") or msg.get("parts", "")
    if isinstance(content, dict):
        if "parts" in content and isinstance(content["parts"], list):
            return " ".join(str(p) for p in content["parts"])
        return str(content.get("text", ""))
    if isinstance(content, list):
        return " ".join(str(x) for x in content)
    return str(content or "")


async def ensure_test_user(session: AsyncSession) -> User:
    user = await session.get(User, DEFAULT_TEST_USER_ID)
    if user:
        return user
    user = User(
        id=DEFAULT_TEST_USER_ID,
        email="test@example.com",
        hashed_password="temp",
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        created_at=datetime.utcnow(),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def load_openai_export(json_path: Path):
    print(f"📁 Loading export: {json_path}")

    with open(json_path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    convs = list(normalize_chatgpt(data))
    print(f"   Conversations found: {len(convs)}")

    # Build database URL from settings (matches Docker compose)
    database_url = settings.DATABASE_URL or (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

    engine = create_async_engine(database_url, echo=False, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        user = await ensure_test_user(session)

        inserted_messages = 0
        for item in convs:
            # Conversation
            conversation = Conversation(
                id=uuid.uuid4(),
                user_id=user.id,
                external_id=item.get("id") or item.get("conversation_id") or "",
                title=item.get("title") or "Untitled Conversation",
                provider="chatgpt",
                source_file=json_path.name,
                metadata_=item.get("metadata", {}),
                message_count=len(item.get("messages", [])) if isinstance(item.get("messages"), list) else 0,
                created_at=datetime.utcnow(),
            )
            session.add(conversation)

            # Messages
            messages = item.get("messages", [])
            if not isinstance(messages, list):
                messages = []
            for msg in messages:
                role = msg.get("role") or (msg.get("author", {}) or {}).get("role") or "unknown"
                content = extract_message_content(msg)
                ts = datetime.utcnow()
                m = Message(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    conversation_id=conversation.id,
                    external_id=msg.get("id", ""),
                    role=role,
                    content=content,
                    word_count=len(content.split()) if content else 0,
                    timestamp_value=ts,
                    metadata_=msg.get("metadata", {}),
                    created_at=datetime.utcnow(),
                )
                session.add(m)
                inserted_messages += 1

        await session.commit()
        print(f"✅ Inserted {len(convs)} conversations and {inserted_messages} messages")


async def main_async(path: str):
    export_path = Path(path)
    json_path = find_conversations_json(export_path)
    await load_openai_export(json_path)


def main():
    parser = argparse.ArgumentParser(description="Load OpenAI export into the database")
    parser.add_argument("--path", required=True, help="Path to export folder or conversations.json")
    args = parser.parse_args()

    asyncio.run(main_async(args.path))


if __name__ == "__main__":
    main()


