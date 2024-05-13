import re
from datetime import datetime

from bs4 import BeautifulSoup

from auto.agents.agent_actions import ActionResult, ActionSuccessResult, ActionErrorResult
from auto.agents.base import BaseAgent
from auto.config import Config
from auto.core.llm.base import ChatMessage, ChatRole
from auto.core.llm.gpt import create_chat_completion
from auto.core.memory.base import MemoryProvider
from auto.core.memory.json_file import JSONFileMemory
from auto.core.models.command_registry import CommandRegistry
from auto.core.models.context_item import ContextItem
from auto.core.prompt.prompts import LOCATOR
from auto.globals.global_data import LocationItems, LocationItem
from auto.utils.exceptions import AgentException


class LocationAgent(BaseAgent):
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
        print("【Aium】元素定位准备就绪！")

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

    def prepare(self, html_source_code) -> str:
        soup = BeautifulSoup(html_source_code, 'html.parser')

        # 找到所有的<img>标签
        img_tags = soup.find_all('img')

        # 遍历所有的<img>标签
        for img_tag in img_tags:
            src_attribute = img_tag.get('src')
            if src_attribute and src_attribute.startswith('data:image/'):
                # 如果src属性以"data:image/"开头，说明包含base64数据，将该<img>标签从DOM中移除
                img_tag.extract()

        # 获取<body>标签
        body_tag = soup.body
        # 找到并移除所有<script>标签及其内容
        for script_tag in body_tag.find_all('script'):
            script_tag.extract()
        for script_tag in body_tag.find_all('style'):
            script_tag.extract()
        # 找到并移除具有 style="display: none;" 属性的元素
        for element in body_tag.find_all(style="display: none;"):
            element.extract()
        for element in body_tag.find_all(style="display:none;"):
            element.extract()

        # 定义一个函数，用于去除标签与标签之间的空白缩进
        def remove_whitespace_between_tags(soup):
            for element in soup:
                if isinstance(element, str):
                    # 如果是字符串，使用正则表达式去除空白缩进
                    element.replace_with(re.sub(r'\n\s+', '\n', element))
                else:
                    # 如果是标签，递归调用函数
                    remove_whitespace_between_tags(element)

        # 去除标签与标签之间的空白缩进
        remove_whitespace_between_tags(body_tag)

        # 压缩<body>标签内容为一个字符串
        body_content = str(body_tag)
        return body_content

    def truncated_string(self, original_string: str):
        if not original_string:
            return ""
        max_characters = 512
        middle_index = len(original_string) // 2
        start_index = max(0, middle_index - (max_characters // 2))
        end_index = min(len(original_string), middle_index + (max_characters // 2))
        truncated_string = original_string[start_index:end_index]
        return truncated_string

    def fetch_data_from_ai(self, body_content: str, step_name: str):
        truncated_string = self.truncated_string(body_content)
        content_format = f"""
        请为当前操作找到需要定位的元素:{step_name}; 当前网页源码为:{truncated_string}
        """
        while True:
            memories = self.local_memory.get_memories()
            memories.insert(0, ChatMessage(role=ChatRole.SYSTEM, content=LOCATOR + content_format))
            # 避免重复占用token数，临时存储 结果返回才进行持久化
            # memories.append(ChatMessage(role=ChatRole.USER, content=content_format))

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
                self.memory.add(ChatMessage(role=ChatRole.USER, content=content_format))
                self.memory.add(ChatMessage(role=ChatRole.ASSISTANT, content=response_content))
                break

        # 获取 "locations" 列表
        locations = assistant_reply_dict["data"]["locators"]
        return locations

    def find_element(self, html_source_code, step_name) -> LocationItems:
        """
        定位
        """
        # 创建Beautiful Soup对象并指定解析器

        body_content = self.prepare(html_source_code)

        locations = self.fetch_data_from_ai(body_content, step_name)

        # 创建 LocationItem 对象的列表
        location_items = [LocationItem(item["name"], item["locator"], item["value"], item["desc"]) for item in
                          locations]

        # 创建 LocationItems 对象
        return LocationItems(location_items)

    @staticmethod
    def get_agent_name():
        return "LocationAgent"
