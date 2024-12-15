from agent_base import *
from cprint import *
from copy import deepcopy

from instruction import BASE_SYS_PROMPT_COT as SYS_ACTION
from instruction import CREATIVE_USER_ACTION as USER_ACTION
from instruction import CREATIVE_SYS_REFLECTION as SYS_REFLECTION
from instruction import CREATIVE_SYS_FORESEE_TASK as SYS_FORESEE_TASK
from instruction import CREATIVE_SYS_FORESEE_TOOL as SYS_FORESEE_TOOL
from instruction import REFLECT_ACTS

from utils import find_reflect_function_call, parse_foresee_task_response, parse_foresee_tool_response


class EscapeAgent(BaseAgent):
    def __init__(self, args):
        super().__init__(args)
    
    def format_task_list(self, current_position=None, only_current=False, ignore_notask=False, no_potision=False):
        # map the shown task index into the original task list index
        self.task_index_map = {}
        count = 0
        tasks = ""
        
        # Make position as the key to group tasks
        task_based_on_pos = {}
        for position in self.previous_bad_acts.keys():
            if position not in task_based_on_pos:
                task_based_on_pos[position] = []
        for idx, task in enumerate(self.tasks):
            task_based_on_pos[task[2]].append([task, idx])
        task_based_on_pos = dict(sorted(task_based_on_pos.items(), key=lambda item: len(item[1]), reverse=True))
        
        for position, task_list in task_based_on_pos.items():
            if only_current and position != current_position:
                continue
            if not task_list and ignore_notask:
                continue
            if not no_potision:
                tasks += f"- Position: {position}\n"
            for (task, idx) in task_list:
                tasks += f"[Task Index {count}] Name: {task[0]}, Target Item: {task[3]}\n"
                tasks += f"- Task description: {task[1]}\n\n"
                self.task_index_map[count] = idx
                count += 1
            if not task_list:
                tasks += "No tasks in this scene defined yet.\n"
        tasks = tasks.strip()
        if not tasks:
            tasks = "No tasks defined yet in the task list."
        return tasks


    def maintain_step_positions(self, log):
        if env.global_vars.count.achieve_key_now or env.global_vars.count.collect_tool_now:
            # clear it if making progress
            self.step_postions = []
            self.trigger_new_explore = None
            return
        
        position = log["position"]
        if log["state"] == ["free explore"]:
            self.step_postions.append(position)
        if len(self.step_postions) > 10:
            self.step_postions = self.step_postions[-10:]
 
        # turn positions into a set and get no more than 1 items
        if len(self.step_postions) == 10: # and len(set(self.step_postions)) == 1:
            split_pos = position.split(" -> ")
            target_stack = split_pos if len(split_pos) == 1 else split_pos[:-1]
            # first find the scene this stack has not explored yet
            found = False
            if position in self.scenes_not_explored:
                for _, scene_stack in self.scenes_not_explored[position].items():
                    if scene_stack != None and scene_stack[-1] not in self.all_scenes_explored:
                        target_stack = deepcopy(scene_stack)
                        found = True
                        break
            if not found:
                # start to find scenes not explored
                for _, move_act in self.scenes_not_explored.items():
                    for _, scene_stack in move_act.items():
                        if scene_stack != None and scene_stack[-1] not in self.all_scenes_explored:
                            target_stack = deepcopy(scene_stack)
                            found = True
                            break
                    if found:
                        break
            self.trigger_new_explore = target_stack
    
    
    def reflect(self, log):
        action_answer = log["action_answer"]
        reward = log["response"]
        
        # This dict maintains all the places that the agent has been to
        if log["position"] not in self.previous_bad_acts:
            self.previous_bad_acts[log["position"]] = []
        if log["position"] not in self.previous_good_acts:
            self.previous_good_acts[log["position"]] = []
        # Current step doesn't achieve any concrete effect, update it as a bad action
        if "Change to another scene" not in reward and "move(" not in action_answer:
            if not env.global_vars.count.achieve_key_now and not env.global_vars.count.collect_tool_now and env.global_vars.count.craft_tool_now != None:
                if [action_answer, reward.replace("\n", " ")] not in self.previous_bad_acts[log["position"]]:
                    self.previous_bad_acts[log["position"]].append([action_answer, reward.replace("\n", " ")])
            # Good actions currently not in use ...
            else:
                if [action_answer, reward.replace("\n", " ")] not in self.previous_good_acts[log["position"]]:
                    self.previous_good_acts[log["position"]].append([action_answer, reward.replace("\n", " ")])
        
        # Maintain the scene list to see if explored or not
        if "move(" in action_answer:
            scene_act = action_answer.split("move(")[1].split(")")[0].strip()
            if scene_act in self.scenes_not_explored[log["position"]]:
                self.scenes_not_explored[log["position"]][scene_act] = None
        
        # Maintain the foresee action list, post-process if model is trying actions proposed in foresee
        if self.foresee_actions != []:
            if self.same_action(action_answer, self.foresee_actions[0][1]):
                self.foresee_actions.pop(0)
                if self.foresee_actions == [] and "Action executed successfully" not in reward:
                    # put the last position to current action
                    all_pos = self.position_before_tasks.split(" -> ")
                    self.scene_stack = all_pos
                    self.graph.current_scene = all_pos[-1]
                    self.position_before_tasks = None
            # if the action is successful, then the model should return to normal exploration mode
            if "Action executed successfully" in reward: 
                self.foresee_actions = []
                self.position_before_tasks = None
        
        # update parameter new_tool_collected
        if env.global_vars.count.collect_tool_now:
            last_tool_names = list(env.global_vars.bag.tools.keys())[-1]
            self.new_tool_collected = env.global_vars.bag.tools[last_tool_names] # It should be a tool
        elif env.global_vars.count.craft_tool_now != None:
            craft_tool_name = env.global_vars.count.craft_tool_now
            self.new_tool_collected = env.global_vars.bag.tools[craft_tool_name] # It should be a tool            
        
        # No reflection step for some actions (early exit!)
        if not ("apply(" in action_answer or "input(" in action_answer \
            or ("click(" in action_answer and "You have just collected" not in reward and "Change to another scene" not in reward)) \
            or reward.startswith("Error raised during reaction"):
            log["reflect"] = {"action": "none()", "thought": "No reflection step for current act"}
            return
        
        interact_item = self.graph.current_arg_name
        
        item_in_list = False
        task_idx = None
        for idx, task in enumerate(self.tasks):
            if task[3] == interact_item:
                item_in_list = True
                task_idx = idx
                break
        
        # When initialize the new task, sometimes it's after the first action already failed
        current_act = None
        
        if "Action executed successfully." in reward:
            if "is still missing something else" not in reward:
                if item_in_list:
                    # We perform automatic deletion
                    task_name = self.tasks.pop(task_idx)[0]
                    log["reflect"] = {"action": f"delete({task_name})", "thought": "Task completed and deleted from the task list."}
                    return
                else:
                    # This happens because the model is still exploring and by luck got the right action in first trial
                    log["reflect"] = {"action": "none()", "thought": "No reflection step for current act"}
                    return
            else:
                if item_in_list:
                    # We perform automatic deletion
                    self.tasks.pop(task_idx)
                # Explore the scene and get a right action by luck, still needs to be added to the task list
                actions = ["new"]
        else:
            # The action failed, get the action answer string
            if "click(" in action_answer:
                current_act = "simple click"
            elif "apply(" in action_answer:
                tool = action_answer.split("apply(")[1].split(",")[0].strip()
                current_act = f"apply {tool}"
            elif "input(" in action_answer:
                input_string = action_answer.split("input(")[1].split(",")[0].strip()
                current_act = f"input {input_string}"
            if item_in_list:
                # An automatic way to update the task
                ori_strategy = self.tasks[task_idx][1].strip()
                task_name = self.tasks[task_idx][0]
                # add the current action to the list of tried actions
                if " but all failed." not in ori_strategy:
                    new_strategy = ori_strategy + " I tried " + current_act + " but all failed."
                else:
                    previous_segment = ori_strategy.split(" but all failed.")[0]
                    if current_act not in previous_segment:
                        new_strategy = previous_segment + f", {current_act} but all failed."
                    else:
                        new_strategy = ori_strategy
                self.tasks[task_idx][1] = new_strategy
                log["reflect"] = {"action": f"update({task_name}, {new_strategy})", "thought": "Task updated with the new strategy."}
                return
            else:
                # First try but failed, use new to add a new task
                actions = ["new"]
        
        # form the system prompt based on the current action
        function_list = ", ".join([REFLECT_ACTS[action][1] for action in actions]).strip()
        param_explain = "- " + "\n- ".join([REFLECT_ACTS[action][2] for action in actions]).strip()
        use_example = ", ".join([REFLECT_ACTS[action][3] for action in actions]).strip()
        sys_prompt = SYS_REFLECTION.replace("<function_list>", function_list).replace("<param_explain>", param_explain).replace("<use_example>", use_example)
        
        # begin reflection on the current action
        prompt = ""
        prompt += "Your current position:\n" + log["position"] + '\n\n'
        prompt += log["scene"] + '\n\n'
        prompt += log["possible_actions"] + '\n\n'
        prompt += "Your action: " + log["action_answer"] + "\n\n"
        prompt += "Response from the environment:\n" + log["response"] + "\n\n"

        prompt += "Now please make an action call to maintain the task list in one line. Follow the system instruction to extract hint and fill in the parameter for the function call.\n\nYour Response:\n"
        
        print("\n -=-=-=-=-=-=-=-=-=-=- Reflection USER -=-=-=-=-=-=-=-=-=-=- \n")
        cprint.ok(prompt)
        print()
        
        thought = call_LLM(self.controller, sys_prompt, prompt, self.is_api, self.port)
        action = find_reflect_function_call(thought)
        cprint.info(thought)
        
        try:
            # Other action besides new is maintained in an automatic way
            if action.startswith("new"):
                task_name = action.split('(')[1].split(',')[0]
                task_name = task_name.replace('(', '').replace(') ', '').strip()
                new_strategy_segs = action.split('(')[1].split(',')[1:]
                new_strategy = ",".join(new_strategy_segs).replace('(', '').replace(')', '').strip()
                new_strategy = new_strategy + "." if not new_strategy.endswith(".") else new_strategy
                # add the current action tried but failed to the new task
                if current_act is not None:
                    new_strategy += f" I tried {current_act} but all failed."
                new_task_created = [task_name, new_strategy, log["position"], interact_item]    
                self.tasks.append(new_task_created)
                # updated the parameter new_task_created: task, its index
                self.new_task_created = [new_task_created, len(self.tasks)-1]
            log["reflect"] = {"action": action, "thought": thought}
        except Exception as e:
            print("Error occurs in parsing reflection: " + e)
            log["reflect"] = {"action": "none()", "thought": "Error occurs in parsing reflection: " + thought}
        return


    def take_action(self, scene_prompt, log):
        step = log["step"]
        position = log["position"]
        
        # Maintain the scene list if come to it the first time:
        if position not in self.scenes_not_explored:
            self.scenes_not_explored[position] = {}
        # Maintain the list of all visited scenes
        current_scene = position.split(" -> ")[-1]
        if current_scene not in self.all_scenes_explored:
            self.all_scenes_explored.append(current_scene)
        for line in log['possible_actions'].split('\n'):
            if "<interactable scene>" in line:
                scene_act = line.split("<interactable scene>")[1].split(":")[0].strip()
                if scene_act not in self.scenes_not_explored[position]:
                    new_scene_name = line.split("<interactable scene>")[1].split(": It leads to")[1].strip()
                    split_pos = position.split(" -> ")
                    # update the position
                    if new_scene_name not in split_pos:
                        split_pos.append(new_scene_name)
                        scene_stack = split_pos
                    else:
                        idx = split_pos.index(new_scene_name)
                        scene_stack = split_pos[:idx + 1]
                    self.scenes_not_explored[position][scene_act] = scene_stack
                    
        # Give Scene Description and Possible Actions
        prompt = f"Now you need to act on [Step {step}]\n" + scene_prompt + "\n\n"

        # if getting stuck
        if self.stuck:
            print("\n -=-=-=-=-=-=-=-=-=-=- Action Help -=-=-=-=-=-=-=-=-=-=- \n")
            prompt += self.form_helper_prompt(position, position, self.helper[0]["action_answer"])
            prompt += "Please follow the hint and give your action based on the hint. Your Response:\n"
        # if currently trying a target action proposed
        elif self.foresee_actions != []:
            print("\n -=-=-=-=-=-=-=-=-=-=- Action Try -=-=-=-=-=-=-=-=-=-=- \n")
            first_action = self.foresee_actions[0]
            prompt += f"You are currently trying a target action. Please directly output the following action that you aim to try:\n{first_action[1]}\n\nPlease directly output the action above. Your Response:\n"
        # if currently trying to perform a craft
        elif self.prompt_craft:
            print("\n -=-=-=-=-=-=-=-=-=-=- Action Craft -=-=-=-=-=-=-=-=-=-=- \n")
            prompt += "Please first think about if you could use one <applicable tool> in your bag to another one through action 'craft'. If not, please try to give another action you want to try, but do not repeat the action in history. Your Response:\n"
            # only add history to normal explore steps
            if self.memory > 0 and step > 0:
                k = min(10, step)
                prompt = self.add_history(step, k) + prompt #add previous steps
        # Normal situation
        else:
            print("\n -=-=-=-=-=-=-=-=-=-=- Action Normal -=-=-=-=-=-=-=-=-=-=- \n")
            # Add the previous bad actions done here so that to avoid
            if position in self.previous_bad_acts and len(self.previous_bad_acts[position]) > 0:
                bad_acts_string = ""
                for idx, bad_act in enumerate(self.previous_bad_acts[position][-5:]):
                    bad_acts_string += f"{bad_act[0]}, "
                bad_acts_string = bad_acts_string.strip().strip(',') + ".\n"
                prompt += "Previously you have tried these bad actions here but all failed:\n"
                prompt += bad_acts_string
                prompt += f"Do not repeat these actions listed here.\n\n"
            
            # Add the scenes haven't been explored as a hint
            not_explored_scenes = ""
            for scene_act, value in self.scenes_not_explored[position].items():
                if value != None:
                    not_explored_scenes += f"{scene_act}, "
            if not_explored_scenes:
                not_explored_scenes = not_explored_scenes.strip().strip(',') + ".\n"
                prompt += "Here are the nearby <interactable scenes> that you haven't explored before:\n"
                prompt += not_explored_scenes
                prompt += "Consider moving to these scenes after you have interacted with all items in this scene.\n\n"
                
            prompt += USER_ACTION
        
            # only add history to normal explore steps
            if self.memory > 0 and step > 0:
                k = min(10, step)
                prompt = self.add_history(step, k) + prompt #add previous steps
        
        cprint.err(prompt)
        print()
        
        '''call LLM and make an action'''
        if self.stuck and self.stuck_in_help >= 10:
            # Give direct answer if still stuck after 10 steps of help
            action = self.helper[0]["action_answer"]
        else:
            # get answer from LLM
            action = call_LLM(self.controller, SYS_ACTION, prompt, self.is_api, self.port) 
        
        log["action"] = action.strip()
        action_answer = find_last_function_call(action)
        log["action_answer"] = action_answer.strip()
        cprint.info(action)
        return
    
    
    def forethought(self, log):
        if self.new_tool_collected:
            print("\n -=-=-=-=-=-=-=-=-=-=- Forethought Tool -=-=-=-=-=-=-=-=-=-=- \n")
            # Give the prompt for the new tool collected
            prompt = f"You have just collected a new tool:\n"
            prompt += f"<collected tool>: {self.new_tool_collected.name}\nDescription: {self.new_tool_collected.current_desc()}\n\n"
            # Add the things in the bag to the prompt
            tools_in_bag = env.global_vars.bag.describe(use_index=False, ignore_tools=[self.new_tool_collected.name]).split("object in the scene:\n")[-1].strip()
            prompt += f"Here are all the other tools in your bag. You may use 'craft' action to combine the new tool with another tool in your bag to craft a new tool:\n{tools_in_bag}\n\n"
            # Add the task list to the prompt
            task_list = self.format_task_list(ignore_notask=True, no_potision=True)
            prompt += f"Here a list of tasks waiting to be solved. You may use 'apply' action to apply currently collected tool to a Target Item in a task and try to solve it:\n{task_list}\n\n"
            # Tail of the prompt
            prompt += f"Please follow the system prompt to output your Thought and Actions. You should analyze thoroughly and be bold to propose all plausible craft and apply actions. Your response:\n"
            cprint.err(prompt)
            print()
            response = call_LLM(self.controller, SYS_FORESEE_TOOL, prompt, self.is_api, self.port)
            response = response.replace("\n\n", "\n").strip()
            cprint.info(response)
            
            # Parse the response to get the action
            tool_name_list = [tool.name for tool in env.global_vars.bag.tools.values()]
            current_tool_name = self.new_tool_collected.name
            thought, actions = parse_foresee_tool_response(response, self.tasks, tool_name_list, current_tool_name)
            
            self.foresee_actions = deepcopy(actions)
            log["foresee"] = {"cause": "new_tool_collected", "response": response, "thought": thought, "actions": actions}
            if len(self.foresee_actions) > 0:
                self.position_before_tasks = self.history[-1]["position"]
            
        if self.new_task_created:
            print("\n -=-=-=-=-=-=-=-=-=-=- Forethought Task -=-=-=-=-=-=-=-=-=-=- \n")
            # Give the prompt for the new task created
            prompt = f"The current task that you are trying to solve now:\n"
            prompt += f"[Task] Name: {self.new_task_created[0][0]}, Target Item: {self.new_task_created[0][3]}\n{self.new_task_created[0][1]}\n\n"
            # Add the things in the bag to the prompt
            tools_in_bag = env.global_vars.bag.describe(use_index=False).split("object in the scene:\n")[-1].strip()
            prompt += f"Here are all the tools in your bag. You may use 'apply' action to apply a tool to the Target Item in current task and try to solve it:\n{tools_in_bag}\n\n"
            # Add the memory pad hint to the prompt
            prompt += f"Here are the hints from the memory pad. You may them as reference when deciding how to solve current task:\n{self.memory_pad}\n\n"
            # Tail of the prompt
            prompt += f"Please follow the system prompt to output your Thought and Actions. You should analyze thoroughly and be bold to propose all plausible click, apply, and input actions. Your response:n"
            cprint.err(prompt)
            print()
            response = call_LLM(self.controller, SYS_FORESEE_TASK, prompt, self.is_api, self.port)
            response = response.replace("\n\n", "\n").strip()
            cprint.info(response)
            
            # Parse the response to get the action
            tool_name_list = [tool.name for tool in env.global_vars.bag.tools.values()]
            target_item_name = self.new_task_created[0][3]
            target_task_index = self.new_task_created[1]
            thought, actions = parse_foresee_task_response(response, tool_name_list, target_item_name, target_task_index)
            
            self.foresee_actions = actions
            log["foresee"] = {"cause": "new_task_created", "response": response, "thought": thought, "actions": actions}
            if len(self.foresee_actions) > 0:
                self.position_before_tasks = self.history[-1]["position"]
            
        # Early exit for special situations
        if self.stuck:
            pass
        
        # Give the default value to these two
        self.new_tool_collected = None
        self.new_task_created = None
        self.prompt_craft = False
        return
        
        
    def act(self, step):
        log = {"step": step}
        
        # give a pre-thinking before doing action 
        self.forethought(log)
        
        # Go to position for task execution
        if self.stuck:
            self.stuck_in_help += 1
            self.foresee_actions = []
            self.position_before_tasks = None
            target_position = self.helper[0]["position"]
            all_pos = target_position.split(" -> ")
            self.scene_stack = all_pos
            self.graph.current_scene = all_pos[-1]
            log["position"] = target_position
            log["state"] = ["need help", self.helper[0]]
        elif self.foresee_actions != []:
            self.stuck_in_help = 0
            first_action = self.foresee_actions[0]
            if first_action[0] != "craft":
                task_index = first_action[-1]
                target_position = self.tasks[task_index][2]
                all_pos = target_position.split(" -> ")
                self.scene_stack = all_pos
                self.graph.current_scene = all_pos[-1]
                log["position"] = target_position
            else:
                log["position"] = self.format_scene_stack()
            log["state"] = ["try action", first_action]
        elif self.trigger_new_explore != None:
            self.stuck_in_help = 0
            self.scene_stack = self.trigger_new_explore
            self.graph.current_scene = self.trigger_new_explore[-1]
            log["position"] = self.format_scene_stack()
            log["state"] = ["force new explore"]
            self.trigger_new_explore = None
            self.step_postions = []
            self.prompt_craft = True
        else:
            self.stuck_in_help = 0
            self.update_scene_stack()
            log["position"] = self.format_scene_stack()
            log["state"] = ["free explore"]
        
        # describe the scene and possible actions, prepare to put it in action prompt
        scene_prompt = self.graph.describe(self.scene_stack).strip()
        p1 = scene_prompt.find("Possible Actions:")
        p2 = scene_prompt.find("Tools in Bag:")
        log["scene"] = scene_prompt[:p1].strip()
        log['possible_actions'] = scene_prompt[p1:p2].strip()
        log["bag"] = scene_prompt[p2:].strip()
        
        # begin to take action
        self.take_action(scene_prompt, log)
        
        # get the reward from the environment
        reward = self.graph.react(log["action_answer"])
        cprint.warn(reward)
        log["response"] = reward.strip()
        
        # begin reflection on the current action
        self.reflect(log)
        
        # begin to check the step
        self.maintain_step_positions(log)
        
        print("\n -=-=-=-=-=-=-=-=-=-=- Task List -=-=-=-=-=-=-=-=-=-=- \n")
        cprint.warn(json.dumps(self.tasks, indent=2))
        
        # final step
        self.history.append(log)
        if "game end" in reward.lower():
            return True
        else:
            return False

    def setup(self, controller, game_name):
        super().setup(controller, game_name)
        self.tasks = []
        self.previous_bad_acts = {}
        self.previous_good_acts = {}
        self.scenes_not_explored = {}
        self.all_scenes_explored = []
        self.new_tool_collected = None
        self.new_task_created = None
        self.foresee_actions = []
        self.position_before_tasks = None
        self.step_postions = []
        self.trigger_new_explore = None
        self.prompt_craft = False
        self.memory_pad = "There's currently nothing on memory pad."


if __name__ == "__main__":
    args = parse_args()
    judge = EscapeAgent(args)
    for model in args.models:
        for game in args.games:
            cprint.info(f"Now testing: model {model} on {game}")
            judge.run(model, game)