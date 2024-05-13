import json
import os
from typing import List

import openai
from openai.openai_object import OpenAIObject

from auto.core.llm.base import ChatMessage, ChatModelInfo
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

OPEN_AI_CHAT_MODELS = {
    info.name: info
    for info in [
        ChatModelInfo(
            name="gpt-3.5-turbo-0301",
            prompt_token_cost=0.0015,
            completion_token_cost=0.002,
            max_tokens=4096,
        ),
        ChatModelInfo(
            name="gpt-3.5-turbo-0613",
            prompt_token_cost=0.0015,
            completion_token_cost=0.002,
            max_tokens=4096,
            supports_functions=True,
        ),
        ChatModelInfo(
            name="gpt-3.5-turbo-16k-0613",
            prompt_token_cost=0.003,
            completion_token_cost=0.004,
            max_tokens=16384,
            supports_functions=True,
        ),
        ChatModelInfo(
            name="gpt-4-0314",
            prompt_token_cost=0.03,
            completion_token_cost=0.06,
            max_tokens=8192,
        ),
        ChatModelInfo(
            name="gpt-4-0613",
            prompt_token_cost=0.03,
            completion_token_cost=0.06,
            max_tokens=8191,
            supports_functions=True,
        ),
        ChatModelInfo(
            name="gpt-4-32k-0314",
            prompt_token_cost=0.06,
            completion_token_cost=0.12,
            max_tokens=32768,
        ),
        ChatModelInfo(
            name="gpt-4-32k-0613",
            prompt_token_cost=0.06,
            completion_token_cost=0.12,
            max_tokens=32768,
            supports_functions=True,
        ),
    ]
}
# Set aliases for rolling model IDs
chat_model_mapping = {
    "gpt-3.5-turbo": "gpt-3.5-turbo-0613",
    "gpt-3.5-turbo-16k": "gpt-3.5-turbo-16k-0613",
    "gpt-4": "gpt-4-0613",
    "gpt-4-32k": "gpt-4-32k-0613",
}

def create_chat_completion(
    messages: List[ChatMessage],
    *_,
    **kwargs,
) -> OpenAIObject:
    """Create a chat completion using the OpenAI API

    Args:
        messages: A list of messages to feed to the chatbot.
        kwargs: Other arguments to pass to the OpenAI API chat completion call.
    Returns:
        OpenAIObject: The ChatCompletion response from OpenAI

    """
    completion: OpenAIObject = openai.ChatCompletion.create(
        messages=messages,
        **kwargs,
    )
    return completion



if __name__ == '__main__':
    # completion = openai.ChatCompletion.create(
    #   model="gpt-3.5-turbo",
    #   messages=[
    #     {"role": "system",
    #      "content":  INIT},
    #     {"role": "user", "content": "打开百度输入123点击搜索"}
    #   ]
    # )
    # print(completion)
    # print("\n\n")
    # print(completion.choices[0].message)

    data = {
  "role": "assistant",
  "content": "{ \"data\": { \"_global\": { \"browser\": 0, \"rootPath\": \"https://www.baidu.com\", \"currentPath\": \"https://www.baidu.com\", \"pageSource\": null, \"sessionId\": null, \"_id\": null }, \"steps\": [ { \"num\": 1, \"name\": \"\u6253\u5f00\u767e\u5ea6\" }, { \"num\": 2, \"name\": \"\u5728\u641c\u7d22\u6846\u8f93\u5165123\" }, { \"num\": 3, \"name\": \"\u70b9\u51fb\u641c\u7d22\u6309\u94ae\" } ] }, \"thoughts\": \"\u9700\u8981\u5148\u6253\u5f00\u767e\u5ea6\u7f51\u5740\uff0c\u7136\u540e\u5728\u641c\u7d22\u6846\u4e2d\u8f93\u5165'123'\uff0c\u6700\u540e\u70b9\u51fb\u641c\u7d22\u6309\u94ae\u3002\", \"command\": { \"name\": \"taskComplete\", \"args\": { \"reason\": \"\u4efb\u52a1\u5df2\u6210\u529f\u8f6c\u6362\u4e3a\u64cd\u4f5c\u6b65\u9aa4\" } }, \"next\": false }"
}

    content = json.loads(data.get("content"))

    print(content)
