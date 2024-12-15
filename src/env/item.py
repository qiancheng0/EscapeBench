from . import global_vars
from .tool import Tool
from copy import deepcopy

class Item: #any need to zoom in? how to "get out" from the item
    def __init__(self, item):
        self.name = item["name"].strip()

        self.states = item["states"]
        self.current_state = 0

        self.visible = item["visible"] if "visible" in item else True
        self.interactable = item["interactable"] if "interactable" in item else True
        self.parent_scene = None

    def current_desc(self):
        return self.states[self.current_state]["desc"]

    def trigger(self, trigger):
        trigger_name = trigger.split(",")[0].strip()
        args = trigger.split(",")[1:]
        args = [a.strip() for a in args if a.strip() != ""]
        if trigger_name == "change_visible":
            assert len(args) == 1 or len(args) == 3
            if len(args) == 1:
                tgt_visible = True if args[0].lower() == "true" else False
                self.visible = tgt_visible
                return
            # more complex case
            tgt_type = args[0]
            tgt_name = args[1]
            tgt_visible = True if args[2].lower() == "true" else False
            if tgt_type == "scene":
                graph = self.parent_scene.parent_graph
                tgt_scene = graph.scenes[tgt_name]
                tgt_scene.visible = tgt_visible
                return
            if tgt_type == "tool":
                graph = self.parent_scene.parent_graph
                for scene in graph.scenes.values():
                    for name, tool_wrap in scene.tools.items():
                        if name == tgt_name:
                            tgt_tool: Tool = tool_wrap["tool"]
                            tgt_tool.visible = tgt_visible
                            return
            if tgt_type == "item":
                graph = self.parent_scene.parent_graph
                for scene in graph.scenes.values():
                    for name, item_wrap in scene.items.items():
                        if name == tgt_name:
                            tgt_item: Item = item_wrap["item"]
                            tgt_item.visible = tgt_visible
                            return
            assert False, "wrong tgt type for the trigger change_visible, or the annotation could not be found!"
        
        elif trigger_name == "change_interact":
            assert len(args) == 1 or len(args) == 3
            if len(args) == 1:
                tgt_interactable = True if args[0].lower() == "true" else False
                self.interactable = tgt_interactable
                return
            # more complex case
            tgt_type = args[0]
            tgt_name = args[1]
            tgt_interactable = True if args[2].lower() == "true" else False
            if tgt_type == "item":
                graph = self.parent_scene.parent_graph
                for scene in graph.scenes.values():
                    for name, item_wrap in scene.items.items():
                        if name == tgt_name:
                            tgt_item: Item = item_wrap["item"]
                            tgt_item.interactable = tgt_interactable
                            return
            assert False, "wrong tgt type for the trigger change_interact, or the annotation could not be found!"
                        
        elif trigger_name == "change_state":
            assert len(args) == 1 or len(args) == 3
            if len(args) == 1:
                state_num = int(args[0])
                self.current_state = state_num
                return
            # more complex case
            tgt_type = args[0]
            tgt_name = args[1]
            state_num = int(args[2])
            if tgt_type == "item":
                graph = self.parent_scene.parent_graph
                for scene in graph.scenes.values():
                    for name, item_wrap in scene.items.items():
                        if name == tgt_name:
                            tgt_item: Item = item_wrap["item"]
                            tgt_item.current_state = state_num
                            return
            elif tgt_type == "tool":
                graph = self.parent_scene.parent_graph
                for scene in graph.scenes.values():
                    for name, tool_wrap in scene.tools.items():
                        if name == tgt_name:
                            tgt_tool: Tool = tool_wrap["tool"]
                            tgt_tool.current_state = state_num
                            return
                for name, tool in global_vars.bag.tools.items():
                    if name == tgt_name:
                        tool.current_state = state_num
                        return
            assert False, "wrong tgt type for the trigger change_state, or the annotation could not be found!"

        elif trigger_name == "become_tool":
            assert len(args) == 1
            tool_name = args[0].strip()
            new_tool: Tool = self.parent_scene.tools[tool_name]["tool"]
            new_tool.visible = True
            global_vars.bag.add_tool(deepcopy(new_tool))
            global_vars.count.tool_collected += 1
            global_vars.count.collect_tool_now = True
            self.parent_scene.tools.pop(tool_name)
            self.parent_scene.items.pop(self.name)
            self.visible = False
            return

    
    def click(self):
        state = self.states[self.current_state]
        transitions = state["transitions"] if "transitions" in state else []
        output = ""
        overall_executed = False
        for transition in transitions:
            executed = False
            wait_for = transition["wait_for"] if "wait_for" in transition else []
            triggers = transition["trigger"] if "trigger" in transition else []
            for wait in wait_for:
                waited_action = wait.split(",")[0].strip()
                if waited_action == "click":
                    action_string = f"{self.name} {self.current_state} click"
                    if action_string not in global_vars.completed_acts:
                        global_vars.count.key_steps += 1
                        global_vars.count.achieve_key_now = True
                        global_vars.completed_acts.append(action_string)
                    executed = True
                    overall_executed = True
                    break
            if executed:
                for trigger in triggers:
                    self.trigger(trigger)
                if "reward" in transition:
                    output += f"Action executed successfully. You have clicked on {self.name}. " + transition["reward"].strip().capitalize() + "\n"
                else:
                    output += f"Action executed successfully. You have clicked on {self.name}.\n"
        if not overall_executed:
            if "neg_reward" in state:
                output += f"Nothing happens after clicking on {self.name}. " + state["neg_reward"].strip().capitalize()
            else:
                output += f"Nothing happens after clicking on {self.name}."
        return output.strip()

    
    def input(self, content):
        content = str(content)
        state = self.states[self.current_state]
        transitions = state["transitions"] if "transitions" in state else []
        output = ""
        overall_executed = False
        for transition in transitions:
            executed = False
            wait_for = transition["wait_for"] if "wait_for" in transition else []
            triggers = transition["trigger"] if "trigger" in transition else []
            for wait in wait_for:
                waited_action = wait.split(",")[0].strip()
                args = wait.split(",")[1:]
                args = [a.strip() for a in args if a.strip() != ""]
                if waited_action == "input":
                    correct_content = args[0]
                    print(correct_content, '|', content)
                    if correct_content == content:
                        # check if this action is taken before
                        action_string = f"{self.name} {self.current_state} input {content}"
                        if action_string not in global_vars.completed_acts:
                            global_vars.count.key_steps += 1
                            global_vars.count.achieve_key_now = True
                            global_vars.completed_acts.append(action_string)
                        executed = True
                        overall_executed = True
                    else:
                        output += f"{self.name} indeed needs an input but your current input is wrong. You should try other ones or gather other clues first.\n"
                    # there should be at most one input action in the wait for list, so we break here
                    break
            if executed:
                for trigger in triggers:
                    self.trigger(trigger)
                if "reward" in transition:
                    output += f"Action executed successfully. You have given an input {content} to {self.name}. " + transition["reward"].strip().capitalize() + "\n"
                else:
                    output += f"Action executed successfully. You have given an input {content} to {self.name}.\n"
        if not overall_executed:
            if "neg_reward" in state:
                output += "Nothing happens after the input action. " + state["neg_reward"].strip().capitalize()
            else:
                output += "Nothing happens after the input action."
        return output.strip()
    

    def apply(self, bag_index):
        chosen_tool: Tool = global_vars.bag.get_tool(bag_index)
        output = ""

        state = self.states[self.current_state]
        transitions = state["transitions"] if "transitions" in state else []
        overall_executed = False
        for transition in transitions:
            executed = False
            executed_idx = -1
            wait_for = transition["wait_for"] if "wait_for" in transition else []
            triggers = transition["trigger"] if "trigger" in transition else []
            has_wait = False
            for idx, wait in enumerate(wait_for):
                waited_action = wait.split(",")[0].strip()
                args = wait.split(",")[1:]
                args = [a.strip() for a in args if a.strip() != ""]
                if waited_action == "apply":
                    has_wait = True
                    correct_tool_name = args[0]
                    # Have to make sure the tool has reach its state to be applied
                    if correct_tool_name == chosen_tool.name and self.name in chosen_tool.current_apply_to():
                        action_string = f"{self.name} {self.current_state} apply {chosen_tool.name}"
                        if action_string not in global_vars.completed_acts:
                            global_vars.count.key_steps += 1
                            global_vars.count.achieve_key_now = True
                            global_vars.completed_acts.append(action_string)
                        executed = True
                        overall_executed = True
                        executed_idx = idx
                        break
            if has_wait and not executed:
                output += f"{self.name} indeed needs a tool to apply but the current tool is wrong. You should try other tools or gather other clues first.\n"
            if executed:
                # the item side changes
                output += f"Action executed successfully. You have successfully applied {chosen_tool.name} to {self.name}."
                
                # the tool side changes
                empty = chosen_tool.delete_apply_to(self.name)
                # have to make sure the tool has already reaches its final state
                if empty and chosen_tool.current_state + 1 == len(chosen_tool.states):
                    global_vars.bag.delete_tool(chosen_tool.name)
                
                wait_for.pop(executed_idx)
                if len(wait_for) == 0:
                    for trigger in triggers:
                        self.trigger(trigger)
                    if "reward" in transition:
                        output += " " + transition["reward"].strip().capitalize() + "\n"
                    else:
                        output += "\n"
                else:
                    output += f"\nHowever, the apply of {chosen_tool.name} is not enough, and {self.name} is still missing something else ...\n"
        if not overall_executed:
            if "neg_reward" in state:
                output += "Nothing happens after you apply the tool. " + state["neg_reward"].strip().capitalize() + "\n"
            else:
                output += "Nothing happens after you apply the tool."
        return output.strip()

