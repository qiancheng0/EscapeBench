from typing import Dict

class Tool:
    def __init__(self, tool: Dict):
        self.name = tool["name"].strip()
        self.states = tool["states"] # desc:str, optional: wait_for:List[str], apply_to:List[str]
        self.visible = tool["visible"] if "visible" in tool else True
        self.current_state = 0
        
    def describe(self):
        return self.states[self.current_state]["desc"].strip()
    
    def current_wait_for(self):
        return self.states[self.current_state]["wait_for"] if "wait_for" in self.states[self.current_state] else []
    
    def current_apply_to(self):
        return self.states[self.current_state]["apply_to"] if "apply_to" in self.states[self.current_state] else []
    
    def current_desc(self):
        return self.states[self.current_state]["desc"].strip()
    
    def delete_wait_for(self, waited_item):
        # Delete the waited item from the wait_for list
        self.states[self.current_state]["wait_for"].remove(waited_item)
        empty = False if len(self.states[self.current_state]["wait_for"]) > 0 else True
        return empty
    
    def delete_apply_to(self, applied_item):
        # Delete the applied item from the apply_to list
        self.states[self.current_state]["apply_to"].remove(applied_item)
        empty = False if len(self.states[self.current_state]["apply_to"]) > 0 else True
        return empty


