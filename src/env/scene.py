from .item import Item
from .tool import Tool
from copy import deepcopy
from . import global_vars

class Scene:
    def __init__(self, scene):
        self.name = scene["name"].strip()
        self.desc = scene["desc"].strip()
        self.image_path = scene["image_path"] if "image_path" in scene else None
        self.scene_relations = scene["scene_relations"] if "scene_relations" in scene else {}

        self.visible = scene["visible"] if "visible" in scene else True # default is visible
        self.parent_graph = None

        self.items = {}
        if "items" in scene:
            self.load_items(scene["items"])
        self.tools = {}
        if "tools" in scene:
            self.load_tools(scene["tools"])
        self.action_cache = {}
    
    def load_items(self, items):
        for item in items:
            assert "position" in item, "Position is required for each item in the scene."
            name = item["item"]["name"]
            assert name not in items, f"Item {name} is already in the scene."
            new_item = Item(item["item"])
            new_item.parent_scene = self
            self.items[name] = {"position": item["position"], "item": new_item}
    
    def load_tools(self, tools):
        for tool in tools:
            assert "position" in tool, "Position is required for each tool in the scene."
            name = tool["tool"]["name"]
            assert name not in tools, f"Tool {name} is already in the scene."
            new_tool = Tool(tool["tool"])
            self.tools[name] = {"position": tool["position"], "tool": new_tool}

    def describe(self, path=None):
        output = ""
        output += f"You are in the scene '{self.name}'. {self.desc}\n"
        if path:
            path_str = ' -> '.join(path)
            output += f"Your path from the beginning point to this scene is: {path_str}\n"
        if len(self.items) + len(self.tools) > 0:
            output += "Here are the items you can see in this scene:\n"
            for item_wrap in self.items.values():
                item: Item = item_wrap["item"]
                if item.visible:
                    desc = item.current_desc()
                    output += f"- {item_wrap['position']}, there is {item.name}: {desc}\n"
            for tool_wrap in self.tools.values():
                tool: Tool = tool_wrap["tool"]
                if tool.visible:
                    desc = tool.current_desc()
                    output += f"- {tool_wrap['position']}, there is {tool.name}: {desc}\n"
        return output

    def actions(self, use_index):
        self.action_cache = {}
        index = 1
        output = ""
        # output += "You may perform 'click' (tap the item), 'apply' (use things in your bag and apply to item), or 'input' (input a string) to interact with the following items in this scene:\n"
        output += "Here are all the items in the scene that you can perform 'click', 'apply' or 'input':\n"
        for name, item_wrap in self.items.items():
            item: Item = item_wrap["item"]
            if item.visible and item.interactable:
                if use_index:
                    output += f"<{index}> {name}\n"
                else:
                    output += f"<interactable item> {name}\n"
                self.action_cache[index] = ("item", name)
                index += 1
        for name, tool_wrap in self.tools.items():
            tool: Tool = tool_wrap["tool"]
            if tool.visible:
                if use_index:
                    output += f"<{index}> {name}\n"
                else:
                    output += f"<interactable item> {name}\n"
                self.action_cache[index] = ("tool", name)
                index += 1
        if output.endswith("'click', 'apply' or 'input':\n"):
            output = ""
        # output += "You could perform 'click' on the following indexes to further explore or retreat from the scene:\n"
        output += "Here are nearby scenes that you can perform 'move' to further explore:\n"
        for action, name in self.scene_relations.items():
            if self.parent_graph.scenes[name].visible:
                if use_index:
                    output += f"<{index}> {action}\n"
                else:
                    output += f"<interactable scene> {action}: It leads to {name}\n"
                self.action_cache[index] = ("scene", action, name)
                index += 1
        return output, self.action_cache

    def click(self, index):
        cache_content = self.action_cache[index]
        type = cache_content[0]
        # change to another scene
        if type == "tool":
            tool_name = cache_content[1]
            chosen_tool: Tool = self.tools[tool_name]["tool"]
            # Add the tool to the bag
            global_vars.bag.add_tool(deepcopy(chosen_tool))
            global_vars.count.tool_collected += 1
            global_vars.count.collect_tool_now = True
            reward = f"Action executed successfully. You have just collected a {tool_name}. It is put into your bag. You may craft something new with it and other things in the bag, or apply it in the future."
            # remove this tool from the scene
            self.tools.pop(tool_name)
            return reward, self.name
        elif type == "item":
            item_name = cache_content[1]
            chosen_item: Item = self.items[item_name]["item"]
            # TODO: should let the item to perform click
            reward = chosen_item.click()
            return reward, self.name

        assert False, f"Invalid action type during click detected in scene {self.name}."
    
    def move(self, index):
        cache_content = self.action_cache[index]
        type = cache_content[0]
        # change to another scene
        if type == "scene":
            scene_name = cache_content[2]
            reward = "Action executed successfully. Change to another scene: " + scene_name + "."
            return reward, scene_name # whether the scene will change

        assert False, f"Invalid action type detected during move in scene {self.name}."
    
    
    def apply(self, index, bag_index):
        cache_content = self.action_cache[index]
        type = cache_content[0]
        if type == "tool" or type == "scene":
            assert False, "Invalid action. You cannot apply your item in the bag to the target. Please try other actions."
        elif type == "item":
            item_name = cache_content[1]
            chosen_item: Item = self.items[item_name]["item"]
            reward = chosen_item.apply(bag_index)
            return reward
        
        assert False, f"Invalid action type during apply detected in scene {self.name}."
    
    def input(self, index, input_content):
        cache_content = self.action_cache[index]
        type = cache_content[0]
        if type == "tool" or type == "scene":
            assert False, "Invalid action. You cannot input a string to the target. Please try other actions."
        elif type == "item":
            item_name = cache_content[1]
            chosen_item: Item = self.items[item_name]["item"]
            reward = chosen_item.input(input_content)
            return reward
        
        assert False, f"Invalid action type during input detected in scene {self.name}."
