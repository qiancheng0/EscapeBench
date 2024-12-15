import json
import argparse
import os
from cprint import *

import env.global_vars
from env.graph import Graph
from utils import count_gobal, call_LLM, read_jsonl_multiline
from utils import find_last_function_call

from instruction import BASE_SYS_PROMPT as SYS_PROMPT
from instruction import BASE_SYS_PROMPT_COT as SYS_PROMPT_COT
from instruction import HELPER_PROMPT


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=str, nargs="+", default=["game1-1"], help="Path to the graph files.")
    parser.add_argument("--models", type=str, nargs="+", default=["gpt-4o"], help="Models to be evaluated.")
    parser.add_argument("--port", type=str, default="31415", help="The port number for the model server if not api.")
    parser.add_argument("--is_api", action='store_true')
    parser.add_argument("--max_steps", type=int, default=10, help="Maximum number of steps.")
    parser.add_argument("--memory", type=int, default=10, help="")
    parser.add_argument("--use_cot", action='store_true')
    parser.add_argument("--overwrite", action='store_true')
    parser.add_argument("--stuck_steps", type=int, default=-1, help="When no progress is made in X consecutive steps...")
    parser.add_argument("--stuck_behavior", type=str, default="exit", choices=["exit", "help"])
    parser.add_argument("--gpus", type=int, nargs="+", default=[0])
    parser.add_argument("--output_suffix", type=str, default="")
    
    return parser.parse_args()


class BaseAgent:
    def __init__(self, args):
        self.args = args
        self.max_steps = args.max_steps
        self.memory = args.memory
        self.CoT = args.use_cot
        self.stuck_steps = args.stuck_steps if args.stuck_steps != -1 else 100000000
        self.stuck_behavior = args.stuck_behavior
        self.is_api = args.is_api
        self.port = args.port
        self.overwrite = args.overwrite
        cprint.ok("Judge for EscapeBench initialized.")


    def add_history(self, step, k):
        prompt = ""
        history = {}
        for i in range(step - k, step):
            history[i] = ""
            history[i] += f"History: [Step {i}]\n"
            history[i] += "Your position: " + self.history[i]["position"] + '\n'
            history[i] += "Your action: " + self.history[i]["action_answer"] + "\n"
            history[i] += "Response from the environment: " + self.history[i]["response"] + "\n\n"
        
        # add history records one by one within the context window
        for i in range(step - 1, step - 1 - k, -1):
            prompt = history[i] + prompt
            
        if k > 0:
            return prompt
        else:
            return ""
    
    def form_helper_prompt(self, cur_pos, tar_pos, tar_action):
        cur_pos = cur_pos.split("->")[-1].strip()
        tar_pos = tar_pos.split("->")[-1].strip()
        prompt = HELPER_PROMPT.replace("<cur_pos>", cur_pos).replace("<tar_pos>", tar_pos).replace("<tar_action>", tar_action) + '\n\n'
        return prompt

    def update_scene_stack(self):
        scene_name = self.graph.current_scene
        if scene_name not in self.scene_stack:
            self.scene_stack.append(scene_name)
        else:
            # find the first occurrence of the scene
            idx = self.scene_stack.index(scene_name)
            # remove all the scenes after the first occurrence
            self.scene_stack = self.scene_stack[:idx + 1]
    
    
    def format_scene_stack(self):
        scene_seq =  " -> ".join(self.scene_stack)
        return scene_seq


    def take_action(self, scene_prompt, log):
        step = log["step"]
        position = log["position"]
        
        p1 = scene_prompt.find("Possible Actions:")
        log["scene"] = scene_prompt[:p1].strip()
        log['possible_actions'] = scene_prompt[p1:].strip()
        
        '''form the prompt'''
        prompt = scene_prompt + "\n\n"
        if self.stuck:
            prompt += self.form_helper_prompt(position, position, self.helper[0]["action_answer"])
        prompt = f"Now you need to act on [Step {step}]\nYour current position is: {position}.\n" + prompt + "Please try not to repeat previous actions that already fails, and be creative to try different new actions. Your Response:\n"
        print()
        
        if not self.stuck and self.memory > 0 and step > 0:
            k = min(self.memory, step)
            prompt = self.add_history(step, k) + prompt #add previous steps
        
        if self.stuck and self.stuck_in_help >= 10:
            # Give direct answer if still stuck after 10 steps of help ...
            action = self.helper[0]["action_answer"]
        else:
            action = call_LLM(self.controller, SYS_PROMPT_COT if self.CoT else SYS_PROMPT, prompt, self.is_api, self.port)
        
        log["action"] = action.strip()
        action_answer = find_last_function_call(action)
        log["action_answer"] = action_answer.strip()
        cprint.info(action)
        return
        

    def act(self, step):
        log = {"step": step}
        
        if self.stuck:
            self.stuck_in_help += 1
            target_position = self.helper[0]["position"]
            all_pos = target_position.split(" -> ")
            self.scene_stack = all_pos
            # Directlly jump to that target position for quicker help!
            self.graph.current_scene = all_pos[-1]
            log["position"] = target_position
        else:
            self.stuck_in_help = 0
            self.update_scene_stack()
            log["position"] = self.format_scene_stack()
        
        scene_prompt = self.graph.describe().strip()

        self.take_action(scene_prompt, log)

        reward = self.graph.react(log["action_answer"])
        cprint.warn(reward)
        log["response"] = reward.strip()
        log["completed_act"] = env.global_vars.completed_acts
        
        self.history.append(log)
        if "game end" in reward.lower():
            return True
        else:
            return False
    

    def setup(self, controller, game_name):
        '''set the parameters'''
        game_path = os.path.join("..", "data", game_name + ".yaml")
        self.graph = Graph(game_path, use_index=False)
        self.controller = controller
        self.history = []
        self.scene_stack = []
        self.stuck = False
        self.stuck_in_help = 0
        self.helper = None
        self.setup_done = False
        self.help_cnt = 0
        
        if self.stuck_behavior == "help": # self.helper: key steps that haven't been done
            game_id = game_name.replace("-easy", "").replace("-hard", "").replace("game", "")
            refer_path = os.path.join("..", "data", "reference", f"key_log_{game_id}.txt")
            if os.path.exists(refer_path):
                self.helper = read_jsonl_multiline(refer_path)
            else:
                cprint.warn("Warning: helper mode selected but no helper file found.")
        
        env.global_vars.reset_global_vars()
        self.key_step_num, self.tool_num = count_gobal(game_path)
        
        run_id = self.controller.split('/')[-1]
        if self.CoT:
            run_id = run_id + "_cot"
        if self.stuck_behavior == "help":
            run_id = run_id + "_help"
        if self.args.output_suffix:
            run_id = run_id + "_" + self.args.output_suffix
        self.output_dir = os.path.join("..", "outputs", run_id, game_name)

        if os.path.exists(self.output_dir):
            if self.overwrite:
                cprint.warn("Warning: overwriting previous results.")
                os.system(f"rm -r {self.output_dir}")
                os.makedirs(self.output_dir, exist_ok=True)
            else:
                cprint.err("Error: output dir already exists. Skipping evaluation.")
                return False
        else:
            os.makedirs(self.output_dir, exist_ok=True)
            
        json.dump(vars(self.args), open(os.path.join(self.output_dir, "args.json"), "w"), indent=4)
        with open(os.path.join(self.output_dir, "progress.csv"), "w") as file:
            file.write("step\tckpts\ttools\tprogress\thelp\n")
        self.setup_done = True

    def same_action(self, a, b):
        if a.startswith("craft") and b.startswith("craft"):
            arg_a = a.split("(")[1].split(")")[0].split(",")
            arg_a = [x.strip().lower() for x in arg_a]
            arg_b = b.split("(")[1].split(")")[0].split(",")
            arg_b = [x.strip().lower() for x in arg_b]
            return set(arg_a) == set(arg_b)
        else:
            act_a = a.split("(")[0].strip().lower()
            act_b = b.split("(")[0].strip().lower()
            if act_a != act_b:
                return False
            arg_a = a.split("(")[1].split(")")[0].strip().lower().split(",")
            arg_a = [x.strip() for x in arg_a]
            arg_b = b.split("(")[1].split(")")[0].strip().lower().split(",")
            arg_b = [x.strip() for x in arg_b]
            return arg_a == arg_b
    
    def same_position(self, a, b):
        a = a.split("->")[-1].strip()
        b = b.split("->")[-1].strip()
        return a.lower() == b.lower()
    
    def run(self, controller, game_name):
        print("Setting up...")
        self.setup(controller, game_name)
        print("Setup done.")
        if not self.setup_done:
            return False, 0

        '''start running'''
        for i in range(0, self.max_steps):
            escaped = self.act(i)
            progress = round((env.global_vars.count.key_steps + env.global_vars.count.tool_collected) * 100 / (self.key_step_num + self.tool_num), 2)
            self.history[i]["tracking"] = {"key_steps": env.global_vars.count.key_steps, "tool_collected": env.global_vars.count.tool_collected, "total_keys": self.key_step_num, "total_tools": self.tool_num, "progress": progress}

            log = self.history[i]
            with open(os.path.join(self.output_dir, "log.txt"), "a") as file:
                file.write(json.dumps(log, indent=4) + '\n')
            with open(os.path.join(self.output_dir, "progress.csv"), "a") as file:
                file.write(f"{i}\t{env.global_vars.count.key_steps}\t{env.global_vars.count.tool_collected}\t{progress}\t{self.help_cnt}\n")
                
            if (i == 0 and progress > 0) or (progress > self.history[i - 1]["tracking"]["progress"]):
                action_answer = log["action_answer"]
                position = log["position"]
                key_log = None
                for help in self.helper:
                    # craft is regardless of position
                    if self.same_action(help["action_answer"], action_answer) and (self.same_position(help["position"], position) or "craft(" in action_answer):
                        key_log = help
                        break
                if self.helper != None and key_log != None:
                    if self.stuck and key_log == self.helper[0]:
                        self.stuck = False
                    self.helper.remove(key_log)
                with open(os.path.join(self.output_dir, "key_log.txt"), "a") as file:
                    file.write(json.dumps(key_log, indent=4) + '\n')

            if not self.stuck and i >= self.stuck_steps and self.history[i]["tracking"]["progress"] == self.history[i - self.stuck_steps]["tracking"]["progress"]:
                if self.stuck_behavior == "exit":
                    cprint.info(f"You're stuck for {self.stuck_steps} steps, early exit triggered. You progress is: {progress}%")
                    return False, progress
                elif self.helper:
                    cprint.info(f"You're stuck for {self.stuck_steps} steps. Changing to helper mode.")
                    self.stuck = True
                    self.help_cnt += 1
                else:
                    cprint.info(f"You're stuck for {self.stuck_steps} steps. No helper available, exit. You progress is: {progress}%")
                    return False, progress

            cprint.info(f"Current steps: {i}, key steps achieved: {env.global_vars.count.key_steps}/{self.key_step_num}, tools collected: {env.global_vars.count.tool_collected}/{self.tool_num}, progress: {progress}%")
            if escaped:
                cprint.info(f"Congratulations! You solved the puzzle in {i + 1} steps.")
                return True, i + 1
        
        cprint.info(f"Sorry, you didn't solve the puzzle. You progress is: {progress}%")
        return False, progress


if __name__ == "__main__":
    args = parse_args()
    judge = BaseAgent(args)
    for model in args.models:
        for game in args.games:
            cprint.info(f"Now testing: model {model} on {game}")
            judge.run(model, game)