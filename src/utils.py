import yaml
import requests
import time
import json
import re
from openai import OpenAI

api_key = json.load(open("../secret.json", "r"))["api_key"]
base_url = json.load(open("../secret.json", "r"))["base_url"]
client = OpenAI(
    api_key=api_key,
    base_url=base_url,
)


def read_jsonl_multiline(path):
    data = []
    with open(path, 'r', encoding='utf-8') as file:
        json_obj = ''
        for line in file:
            json_obj += line.strip()
            if line.strip().endswith('}'):
                try:
                    data.append(json.loads(json_obj))
                except json.JSONDecodeError as e:
                    print(f"err: {e}")
                json_obj = ''
    return data


def call_model_server(sys_prompt: str, user_prompt: str, port="12345"):
    server_url = f"http://127.0.0.1:{port}/predict"
    try_time = 0
    while try_time < 3:
        try:
            response = requests.post(server_url, json={"sys_prompt": sys_prompt, "user_prompt": user_prompt})
            response.raise_for_status()
            res = response.json()["prediction"]
            return res
        except requests.exceptions.RequestException as e:
            try_time += 1
            print(f"Error connecting to the server: {e}")
            time.sleep(3)
    return "Error in calling LLM."


def call_LLM(model, sys_prompt, prompt, use_api=True, port="12345"):
    return "click(door)"
    if use_api:
        messages = [
            {'role': 'system', 'content': sys_prompt},
            {'role': 'user', 'content': prompt}
        ]
        for _ in range(3):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0,
                    n=1,
                )
                content = response.choices[0].message.content
                return content.strip()
            except Exception as e:
                print(f"Chat Generation Error: {e}")
                time.sleep(5)
        return "Error in calling LLM."
    # If using deployed model instead of API
    else:
        return call_model_server(sys_prompt, prompt, port)


def find_last_function_call(text):
    function_names = ["click", "craft", "apply", "input", "move"]
    pattern = r'\b(?:' + '|'.join(re.escape(fn) for fn in function_names) + r')\s*\([^()]*?\)\s*'
    matches = re.findall(pattern, text)
    return matches[-1] if matches else "No action"


def find_reflect_function_call(text):
    function_names = ["new", "update", "delete", "none"]
    pattern = r'\b(?:' + '|'.join(re.escape(fn) for fn in function_names) + r')\s*\([^()]*?\)\s*'
    matches = re.findall(pattern, text)
    return matches[-1] if matches else "none()"


def parse_foresee_tool_response(response, task_list, tool_name_list, current_tool_name):
    # Initialize variables
    try:
        thought = response.split("- Thought:")[1].split("- Actions:")[0].strip()
    except:
        print("Error in parsing thought in response.")
        thought = ""
    try:
        lines = response.split("- Actions:")[1].strip().split("\n")
    except:
        print("Error in parsing actions in response.")
        lines = response.strip().split("\n")
    actions = []
    # Extract actions
    for line in lines:
        line = line.strip()
        if line:
            # Match craft or apply actions with parameters
            match_craft = re.match(r"- craft\(([^,]+),\s*([^)]+)\)", line)
            match_apply = re.match(r"- apply\(([^,]+),\s*([^)]+)\)", line)
            if match_craft:
                tool, applicable_tool = match_craft.groups()
                if applicable_tool.strip() not in tool_name_list:
                    print(f"Error in parsing craft action: {line}, another tool for crafting not in bag!")
                    continue
                tool = current_tool_name
                applicable_tool = applicable_tool.strip()
                action = f"craft({tool}, {applicable_tool})"
                try:
                    description = line.aplit(":")[1].strip()
                except:
                    description = f"Try craft {tool} with {applicable_tool}! It may work."
                actions.append(["craft", action, description])
            elif match_apply:
                tool, target_item = match_apply.groups()
                task_index_match = re.search(r"Task index (\d+)", line)
                task_index = int(task_index_match.group(1)) if task_index_match else None
                for idx, task in enumerate(task_list):
                    if task[3].strip().lower() == target_item.strip().lower():
                        task_index = idx
                        break
                if task_index is None:
                    print(f"Error in parsing apply action: {line}, target item not in task list!")
                    continue
                tool = current_tool_name
                if task_index >= len(task_list):
                    print(f"Error in parsing apply action: {line}, task index out of range!")
                    continue
                target_item = task_list[task_index][3]
                action = f"apply({tool}, {target_item})"
                try:
                    description = line.aplit(":")[1].strip()
                except:
                    description = f"Apply {tool} to {target_item}! It may work."
                actions.append(["apply", action, description, task_index])
                
    return thought.strip(), actions


def parse_foresee_task_response(response, tool_name_list, target_item_name, target_task_index):
    # Initialize variables
    try:
        thought = response.split("- Thought:")[1].split("- Actions:")[0].strip()
    except:
        print("Error in parsing thought in response.")
        thought = ""
    try:
        lines = response.split("- Actions:")[1].strip().split("\n")
    except:
        print("Error in parsing actions in response.")
        lines = response.strip().split("\n")
    actions = []
    # Extract actions
    for line in lines:
        if line.strip():
            # Match craft or apply actions with parameters
            match_input = re.match(r"- input\(([^,]+),\s*([^)]+)\)", line)
            match_apply = re.match(r"- apply\(([^,]+),\s*([^)]+)\)", line)
            match_click = re.match(r"- click\(([^,]+)\)", line)
            if match_click:
                action = f"click({target_item_name})"
                try:
                    description = line.aplit(":")[1].strip()
                except:
                    description = f"Try click on the {target_item_name} to simply interact! It may work."
                actions.append(["click", action, description, target_task_index])
            if match_input:
                input_string, target_item = match_input.groups()
                target_item = target_item_name
                input_string = input_string.strip()
                action = f"input({input_string}, {target_item})"
                try:
                    description = line.aplit(":")[1].strip()
                except:
                    description = f"Try input {input_string} into {target_item}! It may work."
                actions.append(["input", action, description, target_task_index])
            elif match_apply:
                tool, target_item = match_apply.groups()
                if tool.strip() not in tool_name_list:
                    print(f"Error in parsing apply action: {line}, the tool to be applied not in bag!")
                    continue
                tool = tool.strip()
                target_item = target_item_name
                action = f"apply({tool}, {target_item})"
                try:
                    description = line.aplit(":")[1].strip()
                except:
                    description = f"Apply {tool} to {target_item}! It may work."
                actions.append(["apply", action, description, target_task_index])
                
    return thought.strip(), actions

    
def count_gobal(yaml_path):
    with open(yaml_path, "r") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    wait_count = 0
    tool_count = 0
    for scene in data:
        if "items" in scene:
            for item_wrap in scene["items"]:
                item = item_wrap["item"]
                states = item["states"]
                for state in states:
                    if "transitions" not in state:
                        continue
                    transitions = state["transitions"]
                    for transition in transitions:
                        if "wait_for" in transition:
                            wait_count += len(transition["wait_for"])
        if "tools" in scene:
            for tool_wrap in scene["tools"]:
                tool = tool_wrap["tool"]
                states = tool["states"]
                for state in states:
                    if "wait_for" in state:
                        wait_count += len(state["wait_for"])
        tool_count += len(scene.get("tools", []))
    print(f"wait_count: {wait_count}, tool_count: {tool_count}")
    return wait_count, tool_count


if __name__ == "__main__":
    count_gobal("../data/game0.yaml")