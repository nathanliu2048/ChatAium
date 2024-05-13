import uuid


class IsolateGlobalData:
    browser: str = "chrome"
    rootPath: str = ""
    currentPath: str = ""
    sessionId: str = None
    _id: str = str(uuid.uuid4()).replace('-', '')


class IsolateSteps:
    _id: str = None
    steps = []
    """
        步骤列表
    """


class LocationItem:
    def __init__(self, name, locator, value, desc):
        self.name = name
        self.locator = locator
        self.value = value
        self.desc = desc


class LocationItems:
    def __init__(self, items):
        self.items = items


def map_dict_to_class(dict_data, class_instance):
    for key, value in dict_data.items():
        if hasattr(class_instance, key):
            setattr(class_instance, key, value)
