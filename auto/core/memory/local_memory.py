from typing import Iterator

from auto.core.llm.base import ChatMessage
from auto.core.memory.base import MemoryProvider


class LocalMemory(MemoryProvider):
    """ 临时存储 """
    memories: list[ChatMessage]

    def __init__(self):
        self.memories = []

    def get_memories(self):
        # TODO 限制长度当前只限制10条
        # 返回self.memories中的最后10条记录
        return list(self.memories[-10:])

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
        return len(self.memories)

    def add(self, item: ChatMessage):
        self.memories.append(item)
        return len(self.memories)

    def discard(self, item: ChatMessage):
        try:
            self.remove(item)
        except:
            pass

    def clear(self):
        """Clears the data in memory."""
        self.memories.clear()
