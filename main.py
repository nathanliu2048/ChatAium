from auto.agents.housekeeper import Housekeeper
from auto.commands import COMMAND_CATEGORIES
from auto.config import Config
from auto.core.models.command_registry import CommandRegistry


# 去除带有指定样式的元素
def is_hidden(element):
    style = element.get("style")
    return style and "display: none" in style


code_to_execute = """
def click(id):
    # 在搜索框中输入“今天几号”
    search_box = driver.find_element("id", "kw")
    search_box.send_keys("今天几号")

    # 定位搜索按钮并点击
    search_button = driver.find_element("id", "su")
    search_button.click()
    time.sleep(2)

click("su")
"""

# 执行code_to_execute，并将driver传递给命名空间
if __name__ == '__main__':
    # 注册指令
    command_registry = CommandRegistry.with_command_modules(COMMAND_CATEGORIES, Config())
    print("【Aium】指令加载器初始化完成！")

    # 创建大管家
    housekeeper = Housekeeper(command_registry, Config())

    # 意图
    # intention = "百度搜索今日天气"
    intention = ""

    while True:
        intention = input("请输入...\n")
        if intention is not None and len(intention.strip()) > 0:
            break
        print("输入不能为空！")
    print("\n")

    print(">>>>> USER >>>>>" + intention)

    # 解析意图

    # 初始化操作
    _id, isolate_global, isolate_steps = housekeeper.recognitionIntention(intention)

    housekeeper.startSession(_id, isolate_global, isolate_steps)

    housekeeper.stopSession(_id)
