from __future__ import annotations

import json
import logging
import re
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Literal

from auto.agents.agent_actions import ActionResult
from auto.core.json_utils.utilities import extract_dict_from_response, validate_dict
from auto.core.llm.base import ChatModelResponse
from auto.core.memory.local_memory import LocalMemory
from auto.core.models.command import CommandOutput
from auto.utils.exceptions import (
    AgentException,
    CommandExecutionError,
    InvalidAgentResponseError,
    UnknownCommandError,
)

if TYPE_CHECKING:
    from auto.config import Config
    from auto.core.models.command_registry import CommandRegistry

logger = logging.getLogger(__name__)

CommandName = str
CommandArgs = dict[str, str]
AgentThoughts = dict[str, Any]


class BaseAgent(metaclass=ABCMeta):
    """Base class for all Auto-GPT agents."""

    ThoughtProcessID = Literal["one-shot"]
    ThoughtProcessOutput = tuple[CommandName, CommandArgs, AgentThoughts]

    def __init__(
            self,
            command_registry: CommandRegistry,
            config: Config,
    ):
        self.local_memory: LocalMemory = LocalMemory()
        """ 用于存储当前环节需要执行的上下文 """

        self.command_registry = command_registry
        """The registry containing all commands available to the agent."""

        self.config = config
        """The applicable application configuration."""

        # Support multi-inheritance and mixins for subclasses
        super(BaseAgent, self).__init__()

    @abstractmethod
    def get_memory(self):
        ...

    @abstractmethod
    def execute(
            self,
            command_name: str,
            command_args: dict[str, str] = {},
            user_input: str = "",
    ) -> ActionResult:
        """Executes the given command, if any, and returns the agent's response.

        Params:
            command_name: The name of the command to execute, if any.
            command_args: The arguments to pass to the command, if any.
            user_input: The user's input, if any.

        Returns:
            The results of the command.
        """
        ...

    # This can be expanded to support multiple types of (inter)actions within an agent
    def response_format_instruction(self, thought_process_id: ThoughtProcessID) -> str:
        if thought_process_id != "one-shot":
            raise NotImplementedError(f"Unknown thought process '{thought_process_id}'")

        RESPONSE_FORMAT_WITH_COMMAND = """```ts
        interface Response {
            thoughts: {
                // Thoughts
                text: string;
                reasoning: string;
                // Short markdown-style bullet list that conveys the long-term plan
                plan: string;
                // Constructive self-criticism
                criticism: string;
                // Summary of thoughts to say to the user
                speak: string;
            };
            command: {
                name: string;
                args: Record<string, any>;
            };
        }
        ```"""

        RESPONSE_FORMAT_WITHOUT_COMMAND = """```ts
        interface Response {
            thoughts: {
                // Thoughts
                text: string;
                reasoning: string;
                // Short markdown-style bullet list that conveys the long-term plan
                plan: string;
                // Constructive self-criticism
                criticism: string;
                // Summary of thoughts to say to the user
                speak: string;
            };
        }
        ```"""

        response_format = re.sub(
            r"\n\s+",
            "\n",
            RESPONSE_FORMAT_WITHOUT_COMMAND
            if self.config.openai_functions
            else RESPONSE_FORMAT_WITH_COMMAND,
        )

        use_functions = self.config.openai_functions and self.command_registry.commands
        return (
            f"Respond strictly with JSON{', and also specify a command to use through a function_call' if use_functions else ''}. "
            "The JSON should be compatible with the TypeScript type `Response` from the following:\n"
            f"{response_format}"
        )

    def done(self):
        pass

    def extract_and_validate(self, response_content):
        assistant_reply_dict = extract_dict_from_response(response_content)

        _, errors = validate_dict(assistant_reply_dict, self.config)
        if errors:
            raise InvalidAgentResponseError(
                "Validation of response failed:\n  "
                + ";\n  ".join([str(e) for e in errors])
            )

        # Get command name and arguments
        command_name, arguments = self.extract_command(
            assistant_reply_dict
        )
        response = command_name, arguments, assistant_reply_dict

        return response

    def extract_command(
            self,
            assistant_reply_json: dict
    ) -> tuple[str, dict[str, str]]:
        """Parse the response and return the command name and arguments

        Args:
            assistant_reply_json (dict): The response object from the AI
            assistant_reply (ChatModelResponse): The model response from the AI
            config (Config): The config object

        Returns:
            tuple: The command name and arguments

        Raises:
            json.decoder.JSONDecodeError: If the response is not valid JSON

            Exception: If any other error occurs
        """
        try:
            if not isinstance(assistant_reply_json, dict):
                raise InvalidAgentResponseError(
                    f"The previous message sent was not a dictionary {assistant_reply_json}"
                )

            if "command" not in assistant_reply_json:
                raise InvalidAgentResponseError("Missing 'command' object in JSON")

            command = assistant_reply_json["command"]
            if not isinstance(command, dict):
                raise InvalidAgentResponseError("'command' object is not a dictionary")

            if "name" not in command:
                raise InvalidAgentResponseError("Missing 'name' field in 'command' object")

            command_name = command["name"]

            # Use an empty dictionary if 'args' field is not present in 'command' object
            arguments = command.get("args", {})

            return command_name, arguments

        except json.decoder.JSONDecodeError:
            raise InvalidAgentResponseError("Invalid JSON")

        except Exception as e:
            raise InvalidAgentResponseError(str(e))

    def execute_command(
            self,
            command_name: str,
            arguments: dict[str, str],
            agent: BaseAgent,
    ) -> CommandOutput:
        """Execute the command and return the result

        Args:
            command_name (str): The name of the command to execute
            arguments (dict): The arguments for the command
            agent (Agent): The agent that is executing the command

        Returns:
            str: The result of the command
        """
        # Execute a native command with the same name or alias, if it exists
        if command := agent.command_registry.get_command(command_name):
            try:
                return command(**arguments, agent=agent)
            except AgentException:
                raise
            except Exception as e:
                raise CommandExecutionError(str(e))

        raise UnknownCommandError(
            f"Cannot execute command '{command_name}': unknown command."
        )

    @staticmethod
    def get_agent_name():
        ...
