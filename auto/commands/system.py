"""Commands to control the internal state of the program"""

from __future__ import annotations

from auto.agents.base import BaseAgent
from auto.core.llm.base import ChatMessage, ChatRole

COMMAND_CATEGORY = "system"
COMMAND_CATEGORY_TITLE = "System"

import logging

from auto.core.models.command_decorator import command

logger = logging.getLogger(__name__)


@command(
    "taskComplete",
    "Use this to shut down once you have accomplished all of your goals,"
    " or when there are insurmountable problems that make it impossible"
    " for you to finish your task.",
    {
        "reason": {
            "type": "string",
            "description": "A summary to the user of how the goals were accomplished",
            "required": True,
        }
    },
)
def taskComplete(reason: str, agent: BaseAgent) -> None:
    """
    A function that takes in a string and exits the program

    Parameters:
        reason (str): A summary to the user of how the goals were accomplished.
    Returns:
        A result string from create chat completion. A list of suggestions to
            improve the code.
    """
    print("taskComplete>>>>>>>>>>>>>>>>>>>>>>" + reason)
    agent.done()


@command(
    "askUser",
    "Use this to shut down once you have accomplished all of your goals,"
    " or when there are insurmountable problems that make it impossible"
    " for you to finish your task.",
    {
        "content": {
            "type": "string",
            "description": "A summary to the user of how the goals were accomplished",
            "required": True,
        }
    },
)
def askUser(content: str, agent: BaseAgent) -> None:
    logger.info(content, extra={"title": "ask User...\n"})
    agent.local_memory.add(ChatMessage(role=ChatRole.ASSISTANT, content=content))
    agent.get_memory().add(ChatMessage(role=ChatRole.ASSISTANT, content=content))
    # 等待用户输入
    while True:
        user_input = input(content)
        if user_input is not None and len(user_input.strip()) > 0:
            agent.local_memory.add(ChatMessage(role=ChatRole.USER, content=user_input.strip()))
            agent.get_memory().add(ChatMessage(role=ChatRole.USER, content=user_input.strip()))
            break
        print("请按照要求补充相应信息...")
