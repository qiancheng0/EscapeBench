import yaml
from IPython import embed

path = "./game2-4-hard.yaml"
'''
1. the argument for wait and trigger
2. the data type for all (including whether there's nonetype)
3, make sure everything can be found
'''

data = yaml.safe_load(open(path, "r"))
all_names = []
all_wait_for = []
all_apply_to = []

def check_wait(wait):
    global all_names
    waited_action = wait.split(",")[0].strip()
    args = wait.split(",")[1:]
    args = [a.strip() for a in args if a.strip() != ""]
    if waited_action == "apply":
        assert len(args) == 1, f"Apply should have 1 argument in {wait}."
        name = args[0]
        assert name in all_names, f"Name {name} is not found in {wait}."
        return
    elif waited_action == "click":
        assert len(args) == 0, f"Click should have 0 argument in {wait}."
        return
    elif waited_action == "input":
        assert len(args) == 1, f"Input should have 1 argument in {wait}."
        return
    assert False, f"Waited action {waited_action} is not supported in {wait}."


def check_trigger(trigger):
    global all_names
    trigger_name = trigger.split(",")[0].strip().lower()
    args = trigger.split(",")[1:]
    args = [a.strip() for a in args if a.strip() != ""]
    if trigger_name == "change_visible":
        assert len(args) == 3 or len(args) == 1, f"Change visible should have 1 or 3 arguments in {trigger}."
        if len(args) == 1:
            return
        tgt_type = args[0]
        tgt_name = args[1]
        assert tgt_type in ["scene", "item", "tool"], f"Target type {tgt_type} is not supported in {trigger}."
        assert tgt_name in all_names, f"Target name {tgt_name} is not found in {trigger}."
        
        tgt_tf = True if args[2].lower() == "true" else False
        if tgt_tf:
            for scene in data:
                if scene["name"] == tgt_name:
                    assert tgt_type == "scene", f"Target type should be scene in {trigger}."
                    assert "visible" in scene and not scene["visible"], f"Target visibility should be false for {trigger}."
                if "items" in scene:
                    for item_wrap in scene["items"]:
                        item = item_wrap["item"]
                        if item["name"] == tgt_name:
                            assert tgt_type == "item", f"Target type should be item in {trigger}."
                            assert "visible" in item and not item["visible"], f"Target visibility should be false for {trigger}."
                if "tools" in scene:
                    for tool_wrap in scene["tools"]:
                        tool = tool_wrap["tool"]
                        if tool["name"] == tgt_name:
                            assert tgt_type == "tool", f"Target type should be tool in {trigger}."
                            assert "visible" in tool and not tool["visible"], f"Target visibility should be false for {trigger}."
        return

    elif trigger_name == "change_interact":
        assert len(args) == 3 or len(args) == 1, f"Change interact should have 1 or 3 arguments in {trigger}."
        if len(args) == 1:
            return
        tgt_type = args[0]
        tgt_name = args[1]
        assert tgt_type in ["item"], f"Target type {tgt_type} is not supported in {trigger}."
        assert tgt_name in all_names, f"Target name {tgt_name} is not found in {trigger}."
        
        tgt_tf = True if args[2].lower() == "true" else False
        if tgt_tf:
            for scene in data:
                if "items" in scene:
                    for item_wrap in scene["items"]:
                        item = item_wrap["item"]
                        if item["name"] == tgt_name:
                            assert tgt_type == "item", f"Target type should be item in {trigger}."
                            assert "interactable" in item and not item["interactable"], f"Item interactabilty should be false for {trigger}."
        return
    
    elif trigger_name == "change_state":
        assert len(args) == 3 or len(args) == 1, f"Change state should have 1 or 3 arguments in {trigger}."
        if len(args) == 1:
            state_num = args[0]
            assert state_num.isdigit(), f"State number should be a digit in {trigger}."
            return
        tgt_type = args[0]
        tgt_name = args[1]
        state_num = args[2]
        assert tgt_type in ["item", "tool"], f"Target type {tgt_type} is not supported in {trigger}."
        assert tgt_name in all_names, f"Target name {tgt_name} is not found in {trigger}."
        assert state_num.isdigit(), f"State number should be a digit in {trigger}."
        return
    
    elif trigger_name == "become_tool":
        assert len(args) == 1, f"Become tool should have 1 arguments in {trigger}."
        tool_name = args[0]
        assert tool_name in all_names, f"Tool name {tool_name} is not found in {trigger}."
        
        for scene in data:
            if "tools" in scene:
                for tool_wrap in scene["tools"]:
                    tool = tool_wrap["tool"]
                    if tool["name"] == tool_name:
                        assert "visible" in tool and not tool["visible"], f"Tool visibility should be false in {trigger}."
        return
    
    elif trigger_name == "emit_signal" or trigger_name == "delete_signal":
        return
    assert False, f"Trigger {trigger_name} is not supported in {trigger}."

# round one
for scene in data:
    assert "name" in scene, f"Name is required for the scene {str(scene)}."
    assert "desc" in scene, f"Desc is required for the scene {str(scene)}."
    name = scene["name"]
    assert name not in all_names, f"Name {name} is already in the scene."
    all_names.append(name)

    if "items" in scene:
        for item_wrap in scene["items"]:
            assert "position" in item_wrap, f"Position is required for each item in the scene {str(item_wrap)}."
            assert "item" in item_wrap, f"Item is required for each item in the scene {str(item_wrap)}."
            item = item_wrap["item"]
            assert "name" in item, f"Name is required for each item in the scene {str(item)}."
            assert "states" in item, f"States is required for each item in the scene {str(item)}."
            name = item["name"]
            assert name not in all_names, f"Name {name} already appears for other items."
            all_names.append(name)
            states = item["states"]
            for state in states:
                assert "desc" in state, f"Desc is required for each state in the item {str(state)}."
                if "transitions" not in state:
                    continue
                transitions = state["transitions"]
                for transition in transitions:
                    if not isinstance(transition, dict):
                        print(f"Invalid transition: {transition} (type: {type(transition)})")
                    assert isinstance(transition, dict), f"Transition should be a dictionary, but got {type(transition)}: {str(transition)}"
                    if "wait_for" in transition:
                        assert transition["wait_for"] is not None, f"Wait for is required for each transition in the item {str(transition)}."
                        for wait in transition["wait_for"]:
                            assert wait.strip() != "", f"Wait for cannot be empty in the item {str(transition)}."
                            if wait.startswith("apply"):
                                waited_tool = wait.split(",")[1].strip()
                                assert waited_tool.strip() != "", f"Wait for cannot be empty in the item {str(transition)}."
                                all_wait_for.append(waited_tool)
                                all_apply_to.append(name)
                            if not (wait.startswith("apply") or wait.startswith("click") or wait.startswith("input")):
                                assert False, f"{wait} is not supported, you should first give an action mmong click, input and apply."
                    if "trigger" in transition:
                        assert transition["trigger"] is not None, f"Trigger is required for each transition in the item {str(transition)}."
                        for trigger in transition["trigger"]:
                            assert trigger.strip() != "", f"Trigger cannot be empty in the item {str(transition)}."
    
    if "tools" in scene:
        for tool_wrap in scene["tools"]:
            assert "position" in tool_wrap, f"Position is required for each tool in the scene {str(tool_wrap)}."
            assert "tool" in tool_wrap, f"Tool is required for each tool in the scene {str(tool_wrap)}."
            tool = tool_wrap["tool"]
            assert "name" in tool, f"Name is required for each tool in the scene {str(tool)}."
            assert "states" in tool, f"States is required for each tool in the scene {str(tool)}."
            name = tool["name"]
            assert name not in all_names, f"Name {name} already appears for other tools."
            all_names.append(name)
            states = tool["states"]
            for state in states:
                assert "desc" in state, f"Desc is required for each state in the tool {str(state)}."
                if "wait_for" in state:
                    assert state["wait_for"] is not None, f"Wait for is required for each state in the tool {str(state)}."
                    for wait in state["wait_for"]:
                        assert wait.strip() != "", f"Wait for cannot be empty in the tool {str(state)}."
                        all_wait_for.append(wait)
                        all_apply_to.append(name)

# round 2
for scene in data:
    if "scene_relations" in scene:
        relations = scene["scene_relations"]
        for key, value in relations.items():
            assert value in all_names, f"Scene name {value} is not found in the scene_relations."
    if "items" in scene:
        for item_wrap in scene["items"]:
            item = item_wrap["item"]
            name = item["name"]
            states = item["states"]
            for state in states:
                if "transitions" not in state:
                    continue
                transitions = state["transitions"]
                for transition in transitions:
                    if "wait_for" in transition:
                        for wait in transition["wait_for"]:
                            check_wait(wait)
                    if "trigger" in transition:
                        for trigger in transition["trigger"]:
                            check_trigger(trigger)
    if "tools" in scene:
        for tool_wrap in scene["tools"]:
            tool = tool_wrap["tool"]
            name = tool["name"]
            states = tool["states"]
            for state in states:
                if "apply_to" in state:
                    assert state["apply_to"] is not None, f"Apply to is required for each state in the tool {str(state)}."
                    for apply in state["apply_to"]:
                        assert apply is not None, f"Apply to cannot be empty in the tool {str(state)}."
                        assert apply in all_apply_to, f"Apply to name {apply} is not found in all the things that is waited for (wait for is {name})."
                        all_apply_to.remove(apply)
                        assert name in all_wait_for, f"Wait for name {name} is not found in all the things that is apply to (apply is {apply})"
                        all_wait_for.remove(name)

assert len(all_wait_for) == 0, f"Wait for {all_wait_for} is not found in any transitions. (all left apply to are {all_apply_to})"
assert len(all_apply_to) == 0, f"Apply to {all_apply_to} is not found in any transitions. (all left wait for are {all_wait_for})"
print("All checks passed.")

