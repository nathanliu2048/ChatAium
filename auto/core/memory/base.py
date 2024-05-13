import abc
import logging
from typing import MutableSet

from auto.core.llm.base import ChatMessage

logger = logging.getLogger(__name__)


class MemoryProvider(MutableSet[ChatMessage]):
    @abc.abstractmethod
    def __init__(self):
        pass
