import uuid
from datetime import datetime
from typing import Tuple, Dict, Optional

from auto.agents.agent_actions import ActionResult, ActionSuccessResult, ActionErrorResult
from auto.agents.base import BaseAgent
from auto.agents.location_agent import LocationAgent
from auto.agents.script_agent import ScriptAgent
from auto.config import Config
from auto.core.drivers import DriverExecutor
from auto.core.llm.base import ChatMessage, ChatRole
from auto.core.llm.gpt import create_chat_completion
from auto.core.memory.base import MemoryProvider
from auto.core.memory.json_file import JSONFileMemory
from auto.core.models.command_registry import CommandRegistry
from auto.core.models.context_item import ContextItem
from auto.core.prompt.prompts import INTENTION
from auto.globals.global_data import IsolateGlobalData, map_dict_to_class, IsolateSteps, LocationItems
from auto.utils.exceptions import AgentException


class Housekeeper(BaseAgent):
    def __init__(
            self,
            command_registry: CommandRegistry,
            config: Config,
    ):
        super().__init__(
            command_registry=command_registry,
            config=config,
        )

        self.memory: MemoryProvider = None
        """声明当前Agent的上下文"""

        self.created_at = datetime.now().strftime("%Y%m%d_%H%M%S")
        """Timestamp the agent was created; only used for structured debug logging."""

        self.warriors: Dict[str, BaseAgent] = {}
        """所有管家可以分配的勇士"""

        self.executors: Dict[str, DriverExecutor] = {}
        """初始化驱动桶"""

        print("【Aium】管家为您服务！")

    def get_memory(self):
        return self.memory

    def add_executor(self, id: str, executor: DriverExecutor):
        """新增方法，用于添加一个执行器到字典中。"""
        self.executors[id] = executor

    def get_executor(self, id: str) -> Optional[DriverExecutor]:
        """获取方法，根据名称获取执行器。如果名称不存在，返回 None。"""
        return self.executors.get(id)

    def remove_executor(self, id: str):
        """删除方法，用于从字典中移除指定名称的执行器。如果名称不存在，会引发 KeyError 异常。"""
        if id in self.executors:
            executor = self.get_executor(id)
            if executor is not None:
                executor.close_browser()
            del self.executors[id]
        else:
            raise KeyError(f"Executor '{id}' not found.")

    def add_warrior(self, warrior_name: str, warrior: BaseAgent):
        # 在字典中添加勇士信息
        self.warriors[warrior_name] = warrior

    def get_warrior(self, warrior_name: str):
        # 获取勇士的信息，返回类型为 BaseAgent
        obj = self.warriors.get(warrior_name, None)  # 默认值为 None，可根据需要更改
        return obj

    def execute(
            self,
            command_name: str,
            command_args: dict[str, str] = {},
            user_input: str = "",
    ) -> ActionResult:
        result: ActionResult

        if command_name == "askUser":
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

    def recognitionIntention(self, intention) -> Tuple[str, IsolateGlobalData, IsolateSteps]:
        """
        识别用户意图 并且创建全局数据
        :param intention: 意图
        :return: IsolateGlobalData
        """
        print("【Aium】管家正在识别客户意图：" + intention)

        _id = str(uuid.uuid4()).replace('-', '')
        self.memory = JSONFileMemory(_id, self.get_agent_name())
        """初始化当前Agent的上下文"""

        isolate_global = IsolateGlobalData()
        isolate_steps = IsolateSteps()
        while True:
            memories = self.local_memory.get_memories()
            memories.insert(0, ChatMessage(role=ChatRole.SYSTEM, content=INTENTION))
            # 避免重复占用token数，临时存储 结果返回才进行持久化
            memories.append(ChatMessage(role=ChatRole.USER, content=intention))


            model = "gpt-3.5-turbo"
            chat_completion_kwargs = {
                "model": model,
                "temperature": 0,
                "max_tokens": 2048  # OPEN_AI_CHAT_MODELS[chat_model_mapping[model]].max_tokens / 2 - 1,
            }
            completion = create_chat_completion(memories, **chat_completion_kwargs)
            response_raw = completion.choices[0].message
            response_content = response_raw.content

            # response_content = """
            # {
            #   "data": {
            #     "_global": {
            #       "browser": 0,
            #       "rootPath": "https://www.baidu.com",
            #       "currentPath": "https://www.baidu.com",
            #       "pageSource": null,
            #       "sessionId": null,
            #       "_id": null
            #     },
            #     "steps": [
            #       {
            #         "num": "1",
            #         "name": "访问百度网址"
            #       },
            #       {
            #         "num": "2",
            #         "name": "在搜索框中输入'今日天气'"
            #       },
            #       {
            #         "num": "3",
            #         "name": "点击搜索按钮"
            #       }
            #     ]
            #   },
            #   "thoughts": "用户想要打开百度并搜索今日天气",
            #   "command": {
            #     "name": "taskComplete",
            #     "args": {
            #       "reason": "提取用户意图完成"
            #     }
            #   },
            #   "next": false
            # }
            # """
            command_name, arguments, assistant_reply_dict = self.extract_and_validate(response_content)

            self.execute(command_name, arguments)

            global_data = assistant_reply_dict["data"]["_global"]
            steps = assistant_reply_dict["data"]["steps"]

            # 填充global data
            map_dict_to_class(global_data, isolate_global)
            isolate_global._id = _id

            # 填充步骤列表
            isolate_steps._id = isolate_global._id
            isolate_steps.steps = steps

            print("【Aium】识别完成")
            self.local_memory.clear()

            print("\n【Aium】即将处理的Step列表")
            print(">>>>>>>>>>>>>>>>>> START >>>>>>>>>>>>>>>>>>")
            for step in isolate_steps.steps:
                if 'name' in step and 'num' in step:
                    print(f"【Step {step['num']}】: {step['name']}")
                else:
                    print("Step object is missing required attributes (name and num).")

            print("<<<<<<<<<<<<<<<<<<<  END  <<<<<<<<<<<<<<<<<\n")
            if assistant_reply_dict.get("next") is None or assistant_reply_dict.get("next") is False:
                self.memory.add(ChatMessage(role=ChatRole.USER, content=intention))
                self.memory.add(ChatMessage(role=ChatRole.ASSISTANT, content=response_content))
                break

        return isolate_global._id, isolate_global, isolate_steps

    def done(self):
        print("【Aium】管家当前阶段任务完成")

    def startSession(self, _id, isolate_global, isolate_steps):
        """
        管家开始工作
        1、准备工作
        2、找对应的Agent去做对应的事情
        """

        # 初始化驱动
        manager = DriverExecutor()
        executor = manager.start()
        isolate_global.sessionId = executor.meta_data.session_id

        self.add_executor(_id, executor)
        print("【Aium】浏览器准备完成！")

        self.recruit(isolate_global._id)
        """把有能力的人都叫来"""

        self.doStep(executor.driver, isolate_global, isolate_steps.steps)

    def doStep(self, driver, isolate_global, steps=[]):
        """
        保证整个环境执行的作用域
        """
        for step in steps:
            if 'name' in step and 'num' in step:
                print(f"【Step {step['num']}】: {step['name']}")

                # 定位
                page_source = driver.page_source
                location_agent = self.get_warrior(LocationAgent.get_agent_name())

                location_items: LocationItems = LocationItems([])
                if isinstance(location_agent, LocationAgent):
                    location_items = location_agent.find_element(page_source, step['name'])

                # 生成脚本
                script_code: str = ""
                script_agent = self.get_warrior(ScriptAgent.get_agent_name())
                if isinstance(script_agent, ScriptAgent):
                    script_code = script_agent.generate_script(step['name'], location_items, isolate_global.currentPath)

                # 驱动脚本
                script_agent.exec_script(driver, script_code)

                # 实时更新当前url
                isolate_global.currentPath = driver.current_url


            else:
                print("Step object is missing required attributes (name and num).")

    def recruit(self, global_id: str):
        """
        招募 专项Agent
        """

        location_agent = LocationAgent(self.command_registry, self.config, global_id)
        self.add_warrior(LocationAgent.get_agent_name(), location_agent)
        """负责元素定位"""

        script_agent = ScriptAgent(self.command_registry, self.config, global_id)
        self.add_warrior(ScriptAgent.get_agent_name(), script_agent)
        """负责生成脚本"""

    def stopSession(self, _id):
        """
        管家工作结束
        1、准备结束工作
        2、对应的Agent结束
        """
        self.remove_executor(_id)

    @staticmethod
    def get_agent_name():
        return "HouseKeeper"
