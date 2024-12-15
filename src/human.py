import os
import json
import pickle
import argparse
from cprint import *

import env.global_vars
from env.graph import Graph
from utils import count_gobal

from instruction import BASE_SYS_PROMPT as SYS_PROMPT


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", type=str, default="game1-1", help="The name of game to try.")
    parser.add_argument("--overwrite", action='store_true')
    parser.add_argument("--backup_interval", type=int, default=-1, help="Backup the game process once every how many steps. -1 indicates do backup every step.")
    parser.add_argument("--load_from", type=int, default="-1", help="Continue the game from which step.")
    
    return parser.parse_args()


def update_scene_stack(scene_stack, scene):
    if scene not in scene_stack:
        scene_stack.append(scene)
    else:
        idx = scene_stack.index(scene)
        scene_stack = scene_stack[:idx + 1]
    return scene_stack


def format_scene_stack(scene_stack):
    scene_seq =  " -> ".join(scene_stack)
    return scene_seq


def make_no_index(response, object_dic, tool_dic):
    try:
        action = response.split("(")[0].strip()
        args = response.split("(")[1].split(")")[0]
        args = args.split(",")
        args = [a.strip() for a in args if a.strip() != ""]
        
        for id, val in enumerate(args):
            if (action == "apply" and id == 0) or action == "craft":
                args[id] = tool_dic[(int)(val)][1]
            elif action == "input" and id == 0:
                pass
            else:
                args[id] = object_dic[(int)(val)][1]
        return action + '(' + ', '.join(args) + ')'
    except:
        return response


if __name__ == "__main__":
    args = parse_args()
    game_name = args.game
    overwrite = args.overwrite
    backup_interval = args.backup_interval
    load_from = args.load_from
    
    output_dir = os.path.join("..", "outputs", "human", game_name)
    os.makedirs(output_dir, exist_ok=True)
    
    if load_from == -1 and os.path.exists(output_dir):
        if overwrite:
            cprint.warn("Warning: overwriting previous results.")
            os.system(f"rm {output_dir}/*")
            os.makedirs(f"{output_dir}/backup", exist_ok=True)
        else:
            cprint.err("Error: output dir already exists. Skipping evaluation.")
            exit(0)
    else:
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(f"{output_dir}/backup", exist_ok=True)
    
    path = os.path.join("..", "data", f"{game_name}.yaml")
    
    if load_from == -1:
        graph = Graph(path, use_index=True)
        scene_stack = []
        history = [{"tracking": {"key_steps": env.global_vars.count.key_steps, "tool_collected": env.global_vars.count.tool_collected, "total_keys": 0, "total_tools": 0, "progress": 0}}]
    else:
        backup_path = f"{output_dir}/backup/{load_from}"
        graph = Graph(backup_path, load_from_backup=True, use_index=True)
        scene_stack = pickle.load(open(os.path.join(backup_path, "path.pkl"), "rb"))
        history = pickle.load(open(os.path.join(backup_path, "history.pkl"), "rb"))
    
    
    cprint.info("Welcome to the game!")
    cprint.warn(SYS_PROMPT)
    cprint.fatal("Type 'exit' to quit the game.")
    print()

    key_step_num, tool_num = count_gobal(path)
    
    if backup_interval != -1:
        os.system(f"mkdir {output_dir}/backup")

    for i in range(load_from + 1, 10000):
        log = {"step": i}
        
        scene_prompt = graph.describe().strip()
        scene_stack = update_scene_stack(scene_stack, graph.current_scene)
        log["position"] = format_scene_stack(scene_stack)
        
        p1 = scene_prompt.find("Possible actions:")
        log["scene"] = scene_prompt[:p1].strip()
        log['possible_actions'] = scene_prompt[p1:].strip()

        cprint.ok(scene_prompt)
        print()
        
        response = input("Your action:\n").strip()
        if response == "exit":
            break
        print()
        response_no_index = make_no_index(response, graph.scenes[graph.current_scene].action_cache, env.global_vars.bag.action_cache)
        print(response_no_index)
        
        log["action"] = response_no_index
        log["action_answer"] = response_no_index

        reward = graph.react(response)
        
        
        log["response"] = reward.strip()
        cprint.info(reward)
        print()

        progress = round((env.global_vars.count.key_steps + env.global_vars.count.tool_collected) * 100 / (key_step_num + tool_num), 2)
        log["tracking"] = {"key_steps": env.global_vars.count.key_steps, "tool_collected": env.global_vars.count.tool_collected, "total_keys": key_step_num, "total_tools": tool_num, "progress": progress}

        cprint.info(f"Current steps: {i}, key steps achieved: {env.global_vars.count.key_steps}/{key_step_num}, tools collected: {env.global_vars.count.tool_collected}/{tool_num}, progress: {progress}%")

        with open(os.path.join(output_dir, "log.txt"), "a") as file:
            file.write(json.dumps(log, indent=4) + '\n')
        
        
        if log["tracking"]["progress"] > history[-1]["tracking"]["progress"]: # makes new progress in the current step
            with open(os.path.join(output_dir, "key_log.txt"), "a") as file:
                file.write(json.dumps({k: log[k] for k in ["position", "action_answer"]}, indent=4) + '\n')
                
        with open(os.path.join(output_dir, "progress.csv"), "a") as file:
            file.write(f"{i}\t{env.global_vars.count.key_steps}\t{env.global_vars.count.tool_collected}\t{progress}\n")
            
        history.append(log)
        
        if (i + 1) % backup_interval == 0:
            back_up_path = os.path.join(output_dir, "backup", f"{i}")
            os.makedirs(back_up_path, exist_ok=True)
            graph.dump(back_up_path)
            pickle.dump(scene_stack, open(os.path.join(back_up_path, "path.pkl"), "wb"))
            pickle.dump(history, open(os.path.join(back_up_path, "history.pkl"), "wb"))
            
        if "game end" in reward.lower():
            with open(os.path.join(output_dir, "progress.csv"), "a") as file:
                file.write(f"{i}\t{env.global_vars.count.key_steps}\t{env.global_vars.count.tool_collected}\t{100}\n")
            cprint.ok(f"Congratulations! You solved the puzzle in {i} steps.")
            break

        print("\n\n =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=- \n\n")
