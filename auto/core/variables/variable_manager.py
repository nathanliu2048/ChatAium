"""
变量管理器
"""

from typing import Any


class VariableItem:
    def __init__(self, name: str, desc: str, var_type: str, value: Any):
        """
        初始化一个变量项。

        :param name: 变量名
        :param desc: 变量描述
        :param var_type: 变量类型
        :param value: 变量值
        """
        self.name = name
        self.desc = desc
        self.type = var_type
        self.value = value

    def __str__(self):
        return f"VariableItem(name='{self.name}', desc='{self.desc}', type='{self.type}', value={self.value})"
