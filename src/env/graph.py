import yaml
from typing import Dict
from .scene import Scene
from . import global_vars
import pickle
import os

# The out most API
class Graph:
    def __init__(self, path, load_from_backup=False, use_index=False):
        if load_from_backup:
            loaded_obj = pickle.load(open(os.path.join(path, "graph.pkl"), "rb"))
            self.__dict__.update(loaded_obj.__dict__)
            global_vars.load_global_vars(path)
        else:
            scenes = yaml.safe_load(open(path, "r"))
            self.scenes: Dict[str, Scene] = {}
            for scene in scenes:
                new_scene = Scene(scene)
                new_scene.parent_graph = self # set the parent
                self.scenes[scene["name"]] = new_scene

            self.current_scene = list(self.scenes.keys())[0]
            self.current_arg_name = None
            self.use_index = use_index

    # API that gives the environment information to the LLM
    def describe(self, scene_path=None):
        global_vars.count.achieve_key_now = False
        global_vars.count.collect_tool_now = False
        global_vars.count.craft_tool_now = None
        bag_describe = global_vars.bag.describe(self.use_index)
        # if not self.current_item:
        scene = self.scenes[self.current_scene]
        scene_describe = scene.describe(scene_path)
        scene_actions, self.action_cache = scene.actions(self.use_index)
        # output = "Scene description:\n" + scene_describe + "\nPossible actions (click, apply, input):\n" + scene_actions + "\nPossible actions (apply_bag):\n" + bag_describe + "\n"
        output = "Scene Description:\n" + scene_describe.strip() + "\n\nPossible Actions:\n" + scene_actions.strip() + "\n\nTools in Bag:\n" + bag_describe.strip()
        return output
    
    def parse_response(self, response):
        # Parse the response
        action = response.split("(")[0].strip()
        args = response.split("(")[1].split(")")[0]
        args = args.split(",")
        args = [a.strip() for a in args if a.strip() != ""]
        
        # check the number of arguments
        if action == "click" and len(args) != 1:
            raise ValueError("Click action should have 1 argument.")
        if action == "move" and len(args) != 1:
            raise ValueError("Move action should have 1 argument.")
        if action == "apply" and len(args) != 2:
            raise ValueError("Apply action should have 2 arguments.")
        if action == "input" and len(args) != 2:
            raise ValueError("Input action should have 2 arguments.")
        if action == "craft" and len(args) != 2:
            raise ValueError("Craft action should have 2 arguments.")

        if not self.use_index:
            reverse_mapping_obj = {}
            reverse_mapping_scene = {}
            reverse_mapping_bag = {}
            for key, value in self.scenes[self.current_scene].action_cache.items():
                if value[0] == "scene":
                    reverse_mapping_scene[value[1].lower()] = key
                else:
                    reverse_mapping_obj[value[1].lower()] = key
            for key, value in global_vars.bag.action_cache.items():
                reverse_mapping_bag[value[1].lower()] = key
            for id, arg in enumerate(args):
                try:
                    if action == "move":
                        args[id] = reverse_mapping_scene[arg.lower()]
                    elif (action == "apply" and id == 0) or action == "craft":
                        args[id] = reverse_mapping_bag[arg.lower()]
                    elif action == "input" and id == 0:
                        pass
                    else:
                        args[id] = reverse_mapping_obj[arg.lower()]
                except:
                    raise ValueError(f"{arg.lower()} is an invalid interactive for your chosen action.")
        else:
            for id, arg in enumerate(args):
                if action == "input" and id == 0:
                    args[id] = str(arg)
                else:
                    args[id] = int(arg)

        # action should be "click", "apply", or "craft"
        return action, args

    # API that receive the response from LLM and return the reward
    def react(self, response):
        try:
            action, args = self.parse_response(response)
            scene: Scene = self.scenes[self.current_scene]
            if action == "click":
                index = int(args[0])
                self.current_arg_name = self.action_cache[index][-1]
                # update the current scene and item
                reward, self.current_scene = scene.click(index)
                return reward
            elif action == "move":
                index = int(args[0])
                self.current_arg_name = None
                # update the current scene and item
                reward, self.current_scene = scene.move(index)
                return reward
            elif action == "apply":
                index = int(args[1])
                bag_index = int(args[0])
                self.current_arg_name = self.action_cache[index][-1]
                reward = scene.apply(index, bag_index)
                return reward
            elif action == "input":
                index = int(args[1])
                input_content = args[0]
                self.current_arg_name = self.action_cache[index][-1]
                reward = scene.input(index, input_content)
                return reward
            elif action == "craft":
                index_1 = int(args[0])
                index_2 = int(args[1])
                self.current_arg_name = None
                reward = global_vars.bag.craft(index_1, index_2)
                return reward

            assert False, f"You cannot apply the action {action} in current scene. Please change an action to take."
        
        except Exception as e:
            reward = f"Error raised during reaction: {e} Nothing happens."
            return reward 

    def dump(self, path):
        pickle.dump(self, open(os.path.join(path, "graph.pkl"), "wb"))
        global_vars.dump_global_vars(path)
        