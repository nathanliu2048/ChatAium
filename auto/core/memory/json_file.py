from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Iterator

import orjson

from auto.core.llm.base import ChatMessage
from auto.core.memory.base import MemoryProvider

logger = logging.getLogger(__name__)


class JSONFileMemory(MemoryProvider):
    """Memory backend that stores memories in a JSON file"""

    SAVE_OPTIONS = orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_SERIALIZE_DATACLASS

    file_path: Path
    memories: list[ChatMessage]

    def __init__(self, global_id: str, prefix: str = "default", memory_path: str = "memory_data") -> None:
        """Initialize a class instance

        Args:
            config: Config object

        Returns:
            None
        """
        session_path = f"{memory_path}/{global_id}"
        if not os.path.exists(session_path):
            os.makedirs(session_path)

        self.file_path = Path(f"{memory_path}/{global_id}/{prefix}_context.json")

        self.file_path.touch()
        logger.debug(
            f"Initialized {__class__.__name__} with index path {self.file_path}"
        )

        self.memories = []
        try:
            self.load_index()
            logger.debug(f"Loaded {len(self.memories)} MemoryItems from file")
        except Exception as e:
            logger.warn(f"Could not load empty MemoryItems from file: {e}")
            self.save_index()

    def __iter__(self) -> Iterator[ChatMessage]:
        return iter(self.memories)

    def __contains__(self, x: ChatMessage) -> bool:
        return x in self.memories

    def __len__(self) -> int:
        return len(self.memories)

    def head_add(self, item: ChatMessage):
        """
        头插入
        """
        self.memories.insert(0, item)
        self.save_index()
        return len(self.memories)

    def add(self, item: ChatMessage):
        self.memories.append(item)
        self.save_index()
        return len(self.memories)

    def discard(self, item: ChatMessage):
        try:
            self.remove(item)
        except:
            pass

    def clear(self):
        """Clears the data in memory."""
        self.memories.clear()
        self.save_index()

    def load_index(self):
        """Loads all memories from the index file"""
        if not self.file_path.is_file():
            logger.debug(f"Index file '{self.file_path}' does not exist")
            return
        with self.file_path.open("r") as f:
            logger.debug(f"Loading memories from index file '{self.file_path}'")
            json_index = orjson.loads(f.read())
            for memory_item_dict in json_index:
                self.memories.append(ChatMessage(**memory_item_dict))

    def save_index(self):
        logger.debug(f"Saving memory index to file {self.file_path}")
        with self.file_path.open("wb") as f:
            return f.write(orjson.dumps(self.memories, option=self.SAVE_OPTIONS))
