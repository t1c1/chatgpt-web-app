import json
import zipfile
import tempfile
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog
from datetime import datetime
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import Conversation, Message

logger = structlog.get_logger()


class FileProcessor:
    """Process ChatGPT and Claude export files."""

    def __init__(self, upload_dir: str = "./uploads", db: Optional[AsyncSession] = None):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(exist_ok=True)
        self.db = db

    async def process_chatgpt_export(self, file_path: Path, user_id: str) -> Dict[str, Any]:
        """Process a ChatGPT export file or directory."""

        stats = {
            "conversations_processed": 0,
            "messages_processed": 0,
            "files_processed": [],
            "errors": []
        }

        try:
            if file_path.is_file():
                if file_path.suffix == '.zip':
                    # Extract and process zip file
                    await self._process_zip_export(file_path, user_id, stats)
                elif file_path.suffix == '.json':
                    # Process single JSON file
                    await self._process_json_file(file_path, user_id, stats)
            elif file_path.is_dir():
                # Process directory of export files
                await self._process_directory_export(file_path, user_id, stats)

        except Exception as e:
            logger.error("Error processing ChatGPT export", exc_info=e, file_path=str(file_path))
            stats["errors"].append(f"Processing failed: {str(e)}")

        return stats

    async def process_claude_export(self, file_path: Path, user_id: str) -> Dict[str, Any]:
        """Process a Claude export file or directory."""

        stats = {
            "conversations_processed": 0,
            "messages_processed": 0,
            "files_processed": [],
            "errors": []
        }

        try:
            if file_path.is_file():
                if file_path.suffix == '.zip':
                    # Extract and process zip file
                    await self._process_zip_export(file_path, user_id, stats, is_claude=True)
                elif file_path.suffix == '.json':
                    # Process single JSON file
                    await self._process_json_file(file_path, user_id, stats, is_claude=True)
            elif file_path.is_dir():
                # Process directory of export files
                await self._process_directory_export(file_path, user_id, stats, is_claude=True)

        except Exception as e:
            logger.error("Error processing Claude export", exc_info=e, file_path=str(file_path))
            stats["errors"].append(f"Processing failed: {str(e)}")

        return stats

    async def _process_zip_export(
        self,
        zip_path: Path,
        user_id: str,
        stats: Dict[str, Any],
        is_claude: bool = False
    ):
        """Process a zip export file."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)

            # Process extracted files
            await self._process_directory_export(temp_path, user_id, stats, is_claude)

    async def _process_directory_export(
        self,
        dir_path: Path,
        user_id: str,
        stats: Dict[str, Any],
        is_claude: bool = False
    ):
        """Process a directory containing export files."""

        # Look for JSON files
        json_files = []
        for pattern in ["*.json"]:
            json_files.extend(dir_path.glob(pattern))

        # Also check for nested structure (data/openai/, data/anthropic/)
        data_dir = dir_path / "data"
        if data_dir.exists():
            for provider_dir in data_dir.iterdir():
                if provider_dir.is_dir():
                    for json_file in provider_dir.glob("*.json"):
                        json_files.append(json_file)

        # Process each JSON file
        for json_file in json_files:
            try:
                await self._process_json_file(json_file, user_id, stats, is_claude)
                stats["files_processed"].append(str(json_file.name))
            except Exception as e:
                stats["errors"].append(f"Failed to process {json_file.name}: {str(e)}")

    async def _process_json_file(
        self,
        json_path: Path,
        user_id: str,
        stats: Dict[str, Any],
        is_claude: bool = False
    ):
        """Process a single JSON file."""

        try:
            with open(json_path, 'r', encoding='utf-8', errors='ignore') as f:
                data = json.load(f)

            if is_claude:
                await self._process_claude_json(data, user_id, stats)
            else:
                await self._process_chatgpt_json(data, user_id, stats)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {json_path.name}: {str(e)}")

    async def _process_chatgpt_json(self, data: Any, user_id: str, stats: Dict[str, Any]):
        """Process ChatGPT JSON data."""

        conversations = []

        if isinstance(data, list):
            conversations = data
        elif isinstance(data, dict):
            conversations = data.get("conversations", [])

        for conv_data in conversations:
            if not isinstance(conv_data, dict):
                continue

            conv_external_id = conv_data.get("id") or conv_data.get("conversation_id")
            title = conv_data.get("title", "") or "Untitled"

            conversation_row = None
            if self.db is not None:
                # Try to find existing conversation for this user/external id
                result = await self.db.execute(
                    select(Conversation).where(
                        Conversation.user_id == user_id,
                        Conversation.external_id == str(conv_external_id),
                        Conversation.provider == "chatgpt",
                    )
                )
                conversation_row = result.scalar_one_or_none()

                if conversation_row is None:
                    conversation_row = Conversation(
                        id=uuid4(),
                        user_id=user_id,
                        external_id=str(conv_external_id) if conv_external_id else None,
                        title=title,
                        provider="chatgpt",
                        source_file="conversations.json",
                        message_count=0,
                        word_count=0,
                    )
                    self.db.add(conversation_row)
                    await self.db.flush()
                else:
                    # Update title if empty or changed
                    if title and conversation_row.title != title:
                        conversation_row.title = title

            # Process messages
            messages = conv_data.get("messages", [])
            if not isinstance(messages, list) or not messages:
                # Handle ChatGPT exports that use a mapping structure
                mapping = conv_data.get("mapping")
                if isinstance(mapping, dict):
                    messages = []
                    for node in mapping.values():
                        msg_obj = node.get("message") if isinstance(node, dict) else None
                        if isinstance(msg_obj, dict):
                            messages.append(msg_obj)
            if not isinstance(messages, list) or not messages:
                continue

            stats["conversations_processed"] += 1

            first_dt: Optional[datetime] = None
            last_dt: Optional[datetime] = None
            conv_message_count = 0
            conv_word_count = 0

            for msg_data in messages:
                if not isinstance(msg_data, dict):
                    continue

                role = (
                    (msg_data.get("author") or {}).get("role")
                    if isinstance(msg_data.get("author"), dict)
                    else msg_data.get("role")
                ) or ""
                content = self._extract_message_content(msg_data)

                if content:
                    stats["messages_processed"] += 1
                    conv_message_count += 1
                    conv_word_count += len(content.split())
                    if self.db is not None and conversation_row is not None:
                        # Parse timestamp if present
                        ts_value = None
                        create_time = msg_data.get("create_time") or msg_data.get("timestamp")
                        if isinstance(create_time, (int, float)):
                            try:
                                ts_value = datetime.utcfromtimestamp(create_time)
                            except Exception:
                                ts_value = None
                        elif isinstance(create_time, str):
                            try:
                                ts_value = datetime.fromisoformat(create_time.replace("Z", "+00:00"))
                            except Exception:
                                ts_value = None

                        if ts_value:
                            if first_dt is None or ts_value < first_dt:
                                first_dt = ts_value
                            if last_dt is None or ts_value > last_dt:
                                last_dt = ts_value

                        message_row = Message(
                            id=uuid4(),
                            user_id=user_id,
                            conversation_id=conversation_row.id,
                            external_id=str(msg_data.get("id")) if msg_data.get("id") else None,
                            role=role or "assistant",
                            content=content,
                            word_count=len(content.split()),
                            timestamp_value=ts_value,
                        )
                        self.db.add(message_row)

            if self.db is not None and conversation_row is not None:
                # Update conversation aggregates
                conversation_row.message_count = (conversation_row.message_count or 0) + conv_message_count
                conversation_row.word_count = (conversation_row.word_count or 0) + conv_word_count
                conversation_row.first_message_date = conversation_row.first_message_date or first_dt
                conversation_row.last_message_date = last_dt or conversation_row.last_message_date
                await self.db.flush()

    async def _process_claude_json(self, data: Any, user_id: str, stats: Dict[str, Any]):
        """Process Claude JSON data."""

        conversations = []

        if isinstance(data, list):
            conversations = data
        elif isinstance(data, dict):
            conversations = data.get("conversations", [])

        for conv_data in conversations:
            if not isinstance(conv_data, dict):
                continue

            conv_id = conv_data.get("uuid", "")
            title = conv_data.get("title", "")

            # Process messages
            messages = conv_data.get("messages", [])
            if not isinstance(messages, list):
                continue

            # TODO: Insert conversation into database
            stats["conversations_processed"] += 1

            for msg_data in messages:
                if not isinstance(msg_data, dict):
                    continue

                role = msg_data.get("role", "")
                content = msg_data.get("text", "") or msg_data.get("content", "")

                if content:
                    # TODO: Insert message into database
                    stats["messages_processed"] += 1

    def _extract_message_content(self, msg_data: Dict[str, Any]) -> str:
        """Extract message content from various ChatGPT message formats."""

        # Try different content fields
        content = msg_data.get("content") or msg_data.get("text") or msg_data.get("parts", "")

        if isinstance(content, dict):
            # Handle content with parts
            if "parts" in content:
                return " ".join(str(part) for part in content["parts"])
            return str(content.get("text", ""))

        elif isinstance(content, list):
            # Handle array of content blocks
            return " ".join(str(item) for item in content)

        return str(content)

    def validate_file(self, file_path: Path) -> Dict[str, Any]:
        """Validate an export file before processing."""

        info = {
            "is_valid": False,
            "file_type": None,
            "estimated_size": 0,
            "warnings": []
        }

        try:
            file_size = file_path.stat().st_size
            info["estimated_size"] = file_size

            if file_size > 100 * 1024 * 1024:  # 100MB limit
                info["warnings"].append("File is very large and may take a long time to process")

            if file_path.suffix == '.zip':
                # Validate zip file
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    file_list = zip_ref.namelist()

                    # Check for expected files
                    has_conversations = any('conversations' in f for f in file_list)
                    has_chatgpt_files = any(f.endswith('.json') for f in file_list)

                    if has_conversations or has_chatgpt_files:
                        info["is_valid"] = True
                        info["file_type"] = "chatgpt_export"
                    else:
                        info["warnings"].append("No recognizable conversation files found in zip")

            elif file_path.suffix == '.json':
                # Quick validation of JSON structure
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    # Try to parse first few lines
                    sample = f.read(1024)
                    try:
                        json.loads(sample)
                        info["is_valid"] = True
                        info["file_type"] = "json_export"
                    except json.JSONDecodeError:
                        info["warnings"].append("File does not appear to be valid JSON")

            elif file_path.is_dir():
                # Check directory contents
                json_files = list(file_path.glob("*.json"))
                if json_files:
                    info["is_valid"] = True
                    info["file_type"] = "directory_export"

        except Exception as e:
            info["warnings"].append(f"Validation error: {str(e)}")

        return info




