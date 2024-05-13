import time
from datetime import datetime

from auto.agents.agent_actions import ActionResult, ActionSuccessResult, ActionErrorResult
from auto.agents.base import BaseAgent
from auto.config import Config
from auto.core.llm.base import ChatMessage, ChatRole
from auto.core.llm.gpt import create_chat_completion
from auto.core.memory.base import MemoryProvider
from auto.core.memory.json_file import JSONFileMemory
from auto.core.models.command_registry import CommandRegistry
from auto.core.models.context_item import ContextItem
from auto.core.prompt.prompts import GENERATE_SCRIPT
from auto.globals.global_data import LocationItems
from auto.utils.exceptions import AgentException


class ScriptAgent(BaseAgent):
    """
    负责元素定位
    """

    def __init__(
            self,
            command_registry: CommandRegistry,
            config: Config,
            global_id: str
    ):
        super().__init__(
            command_registry=command_registry,
            config=config,
        )

        self.memory: MemoryProvider = JSONFileMemory(global_id, self.get_agent_name())
        """声明当前Agent的上下文"""

        self.created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        """Timestamp the agent was created; only used for structured debug logging."""
        print("【Aium】脚本Agent准备就绪！")

    def get_memory(self):
        return self.memory

    def execute(
            self,
            command_name: str,
            command_args: dict[str, str] = {},
            user_input: str = "",
    ) -> ActionResult:
        result: ActionResult

        if command_name == "ask_user":
            pass
        else:
            try:
                return_value = self.execute_command(
                    command_name=command_name,
                    arguments=command_args,
                    agent=self,
                )

                # Intercept ContextItem if one is returned by the command
                if type(return_value) == tuple and isinstance(
                        return_value[1], ContextItem
                ):
                    context_item = return_value[1]
                    return_value = return_value[0]
                    print(
                        f"Command {command_name} returned a ContextItem: {context_item}"
                    )

                result = ActionSuccessResult(return_value)
            except AgentException as e:
                result = ActionErrorResult(e.message, e)

            return result

    def fetch_data_from_ai(self, prompt: str, system_prompt: str):

        while True:
            memories = self.local_memory.get_memories()
            memories.insert(0, ChatMessage(role=ChatRole.SYSTEM, content=system_prompt))
            # 避免重复占用token数，临时存储 结果返回才进行持久化
            memories.append(ChatMessage(role=ChatRole.USER, content=prompt))

            model = "gpt-3.5-turbo"
            chat_completion_kwargs = {
                "model": model,
                "temperature": 0,
                "max_tokens": 2048  # OPEN_AI_CHAT_MODELS[chat_model_mapping[model]].max_tokens / 2 - 1,
            }
            completion = create_chat_completion(memories, **chat_completion_kwargs)
            response_raw = completion.choices[0].message
            response_content = response_raw.content

            command_name, arguments, assistant_reply_dict = self.extract_and_validate(response_content)
            self.execute(command_name, arguments)

            if assistant_reply_dict.get("next") is None or assistant_reply_dict.get("next") is False:
                self.memory.add(ChatMessage(role=ChatRole.USER, content=prompt))
                self.memory.add(ChatMessage(role=ChatRole.ASSISTANT, content=response_content))
                break

        # 获取 "locations" 列表
        script_code = assistant_reply_dict["data"]["script_code"]
        return script_code

    def generate_script(self, prompt, location_items: LocationItems, current_path) -> str:
        """
        生成脚本
        """
        # 整理可用元素定位
        element_locators = ""
        for index, item in enumerate(location_items.items, start=1):
            element_locators += f"{index}.d 元素名称：{item.name},描述:{item.desc}，定位类型:{item.locator},定位的值:{item.value}\n"

        replacement_dict = {
            "[[__element_locators__]]": element_locators,
            "[[__current_path__]]": current_path
        }
        # 遍历替换字典中的每个键值对，并将占位符替换为实际值
        system_prompt = GENERATE_SCRIPT
        for placeholder, replacement in replacement_dict.items():
            system_prompt = system_prompt.replace(placeholder, replacement)

        script_code = self.fetch_data_from_ai(prompt, system_prompt)

        # script_code = """
        # def click(id):
        #     # 在搜索框中输入“今天几号”
        #     search_box = driver.find_element("id", "kw")
        #     search_box.send_keys("今天几号")
        #
        #     # 定位搜索按钮并点击
        #     search_button = driver.find_element("id", "su")
        #     search_button.click()
        #     #time.sleep(2)
        #
        # global n
        # n=n+1
        # driver.get("https://www.baidu.com")
        # click("su")
        #         """
        return script_code

    def exec_script(self, driver, script_code: str):
        if script_code is None:
            return

        globals()['driver'] = driver
        globals()['time'] = time
        globals()['n'] = 0

        # TODO 变量表维护
        exec(script_code, globals(), locals())

    @staticmethod
    def get_agent_name():
        return "ScriptAgent"
