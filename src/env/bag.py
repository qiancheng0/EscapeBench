from .tool import Tool
from typing import Dict
from . import global_vars

class Bag:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.action_cache = {}

    def add_tool(self, tool: Tool):
        self.tools[tool.name] = tool

    def delete_tool(self, name):
        self.tools.pop(name)

    def get_tool(self, index):
        content = self.action_cache[index]
        name = content[1]
        return self.tools[name]

    def describe(self, use_index, with_desc=True, ignore_tools=[]):
        if len(self.tools) == 0:
            return "There's currently not tool in your bag."
        else:
            output = f"Here are the tools in your bag. You can perform 'craft' to use two tools in your bag to craft a new one, or perfom 'apply' to apply one tool in your bag to an object in the scene:\n"
            index = 1
            for name, tool in self.tools.items():
                if name in ignore_tools:
                    continue
                if use_index:
                    output += f"<{index}> {name}"
                else:
                    output += f"<applicable tool> {name}"
                if with_desc:
                    output += f": {tool.describe()}"
                output += "\n"
                self.action_cache[index] = ("tool", name)
                index += 1
            return output

    def craft(self, index_1: int, index_2: int):
        tool_1 = self.get_tool(index_1)
        tool_2 = self.get_tool(index_2)

        reward = ""
        if tool_2.name in tool_1.current_wait_for() and tool_1.name in tool_2.current_apply_to():
            reward += f"Action executed successfully. You have successfully crafted {tool_2.current_desc()} and {tool_1.current_desc()} together.\n"
            global_vars.count.key_steps += 1
            global_vars.count.achieve_key_now = True
            global_vars.count.craft_tool_now = tool_1.name
            empty = tool_1.delete_wait_for(tool_2.name)
            if empty:
                tool_1.current_state += 1
                reward += f"You get a new item: {tool_1.current_desc()}. It is put into your bag."
            else:
                reward += f"However, {tool_1.current_desc()} is still missing something ..."
            # delete the craftd tool if the other one has no use
            empty = tool_2.delete_apply_to(tool_1.name)
            # have to make sure the tool has already reaches its final state
            if empty and tool_2.current_state + 1 == len(tool_2.states):
                self.delete_tool(tool_2.name)
            return reward

        if tool_1.name in tool_2.current_wait_for() and tool_2.name in tool_1.current_apply_to():
            reward += f"Action executed successfully. You have successfully crafted {tool_1.current_desc()} and {tool_2.current_desc()} together.\n"
            global_vars.count.key_steps += 1
            global_vars.count.achieve_key_now = True
            global_vars.count.craft_tool_now = tool_2.name
            empty = tool_2.delete_wait_for(tool_1.name)
            if empty:
                tool_2.current_state += 1
                reward += f"You get a new item: {tool_2.current_desc()}. It is put into your bag."
            else:
                reward += f"However, {tool_2.current_desc()} is still missing something ..."
            empty = tool_1.delete_apply_to(tool_2.name)
            # have to make sure the tool has already reaches its final state
            if empty and tool_1.current_state + 1 == len(tool_1.states):
                self.delete_tool(tool_1.name)
            return reward

        reward = "Nothing happens after crafting these two things together. Please try other actions to take."
        return reward
