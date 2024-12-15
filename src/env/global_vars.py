from .bag import Bag
from dataclasses import dataclass
import pickle
import os

@dataclass
class Count:
    key_steps: int = 0
    tool_collected: int = 0
    achieve_key_now: bool = False
    collect_tool_now: bool = False
    craft_tool_now: bool = False

def reset_global_vars():
    global count, bag, completed_acts
    count = Count()
    bag = Bag()
    completed_acts = []
    
def dump_global_vars(path):
    global count, bag
    pickle.dump(count, open(os.path.join(path, "count.pkl"), "wb"))
    pickle.dump(bag, open(os.path.join(path, "bag.pkl"), "wb"))
    
def load_global_vars(path):
    global count, bag
    count = pickle.load(open(os.path.join(path, "count.pkl"), "rb"))
    bag = pickle.load(open(os.path.join(path, "bag.pkl"), "rb"))

count: Count = Count()
bag: Bag = Bag()
completed_acts = []