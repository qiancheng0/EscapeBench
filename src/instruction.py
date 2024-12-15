HELPER_PROMPT = '''Since you're stuck, the system will provide you with a hint. You MUST follow the hint to complete next key step.
The next target location should be: <tar_pos>.
Your next target action should be: <tar_action>.
You should go to the target position and perform the target action. If you are already at the target location, please directly perform the action.'''


BASE_SYS_PROMPT = '''You are in a Room Escape game. You should explore the scene and find out what to do next.
There are three types of interactives: items, which are the interactable things in the scene; tools, which are applicable tools in your bag; scenes, whcih are interactable scenes near your current position.

You can perform one of the following actions:
- click(<interactable item>): Click an <interactable item> to examine it or interact with it. For example, you can examine a door handle that is marked as interactable.
- apply(<applicable tool>, <interactable item>): Apply an <applicable tool> in your bag to an <interactable item>. For example, you can apply a key in your bag to an interactable locked door to open it.
- input(string, <interactable item>): Input a string (only digits and letters) to an <interactable item>. For example, you can input a string password to an interactable combination lock.
- move(<interactable scene>): Move to a nearby <interactable item> to further explore. For example, you can move to the living room to explore more interactable items there.
- craft(<applicable tool>, <applicable tool>): Use one <applicable tool> in bag to another <applicable tool> in bag to craft something new. For example, you can use a battery in bag to a controller in bag to craft a new charged controller.
For instance, some valid actions may be: click(microwave), apply(key, silver chest), craft(controller, battery), input(c79a1, combination lock), move(Go to operation room).

Here are some reminders to consider when solving puzzles:
1. All interactives are explicitly listed in the Possible Actions. You should only use them as parameters of your action, instead of arbitrary items from the scene.
2. Avoid repeating actions done before, avoid going back and forth between scenes, try to do new actions, explore new scenes, find or craft new tools.
3. When you have already settled an aim to solve, try to follow the aim and solve it. When you are exploring freely, try to interact with all interactable items and move to new scenes.

Output one single action with the format above, with no extra content.'''


BASE_SYS_PROMPT_COT = '\n'.join(BASE_SYS_PROMPT.split('\n')[:-1]).strip() + '\n\nPlease respond in two lines. In the first line, give a brief thought on what you plan to do and the reason. In the second line, output one single action following the format above. Please follow the format: \nThought: ...\nAction: ...'


CREATIVE_USER_ACTION = """You are currently exploring the scene freely. You should try explore new scenes, interact with the items through click, input or apply actions, and try crafting new tools:
- If there's still <interactable items> you haven't tried any action to interact with, you should try 'click' them first.
- Otherwise, explore other new <interactable scene> you haven't been to, or going back to parent scene.
- Follow the rules in Possible Actions and system prompt to give a valid action and thought.
Do not repeat actions in history and previous steps. Your Response:"""


CREATIVE_SYS_FORESEE_TOOL = """You are in a Room Escape game. You have to use your creativity to figure out the use of the tool you have just collected.
There are generally two ways about how to use the tool:
1. Combine this tool with another one in your bag to craft a new tool. In this case, use acton 'craft(<collected tool>, <applicable tool>)', e.g. craft(controller, battery) indicates use a battery in your bag you already have to the controller you just collected to craft a charged controller.
2. Apply this tool to a target item in a task to try solve this task. In this case, use action 'apply(<collected tool>, Target Item in a task)', e.g. apply(key, locked cabinet) indicates apply the key you just collected to a locked cabinet to open it.

Here are some general hints that you should follow:
1. Please especially pay attention to the description of the task and the tool, try to find the connection between them to justify your action.
2. In your '- Thought: ...' part in response, you shuold explicitly think about whether there's item in bag for crafting, or task in the list for applying this tool. You should read and infer carefully from the tool descriptions and the task description, evaluate one by one.
3. In your '- Actions: ...' part in response, you should give zero to multiple action calls. For each action, you should follow the format 'craft(<collected tool>, <applicable tool>)' or 'apply(<collected tool>, Target Item in a task)'. If it's a craft action, you should justify why crafting here makes sense. If it's an apply action, you should first give the task index corresponding to the target item, then justify why this tool may solve the task.

Example Response 1:
- Thought: The phone I just collected has an empty slot on the back, seems needing something like a battery.
  - For action craft, there's no existing battery-like things in my bag to craft.
  - For action apply, the only task of cut water pipe seems not related to the phone I just collected. So there seems no plausible action that I could take now.
- Actions:
  No action.

Example Response 2:
- Thought: The scissors I just collected has a sharp blade, so may be used to cut something.
  - For action craft, there's piece of paper hint and a cup, but from their description they do not need cutting.
  - For action apply, Task 0 about get a piece of wire may need a sharp tool to cut a piece off, and Task 3 about look behind the painting may also need a scissors to cut it open and see behind. I should try all of these actions to see if the scissors can be used. 
- Actions:
  - apply(scissors, wire roll): Task index 0, the target item is wire. The scissors can be used to cut the wire.
  - apply(scissors, painting on the wall): Task index 3, the target item is painting. The scissors can be used to cut the painting open."""


CREATIVE_SYS_FORESEE_TASK = """You are in a Room Escape game. You have to use your creativity to figure out if you could use any tools you have now to solve a new task you have just discovered.
There are generally three ways to solve a task:
1. Click the target item to simply interact with it to solve the task. In this case, use action 'click(Target Item in current task)', e.g. click(microwave) indicates click the microwave to examine it and try solve the task.
2. Use the tool in your bag to apply to the target item in the task. In this case, use action 'apply(<applicable tool>, Target Item in current task)', e.g. apply(key, locked cabinate) indicates apply the key in your bag to a locked cabinet to open it.
3. Input a string to the target item in the task. In this case, use action 'input(<any string>, Target Item in current task)', e.g. input(2413, combination lock) indicates input a string password to the combination lock to solve the task.

Here are some general hints that you should follow:
1. Please especially pay attention to the description of the task about what might be needed. Please always first try simple click to interact if haven't done so. Examine the tool description and your memory pad, try to find the connection between them and what this task needs to justify your action.
2. In your '- Thought: ...' part in response, you should explicitly think about whether there's item to click, tool in bag for applying, or hint from memory pad and tools for string input. You should read and infer carefully from the task description, evaluate one by one.
3. In your '- Actions: ...' part in response, you should give zero to multiple action calls. For each action, you should follow the format 'click(Target Item in current task)', 'apply(<applicable tool>, Target Item in current task)', or 'input(<any string>, Target Item in current task)'. You shuold justify why this action may solve the task according to the task description, tool description, and memory pad hint.

Example Response 1:
- Thought: Current task of try getting water from the tap seems needing a container to hold the water.
  - For action click, I haven't tried to click the tap yet, so I should try it first.
  - For action apply, I have only a tape, a key, and a phone in my bag, none of them seems to be used to get water from the tap according to their description. So not a good idea to try apply action for this task.
  - For action input, from task description it doesn't need input a string to solve the task. So not a good idea to try input action for this task.
- Actions:
  - click(tap): The tap may be interacted to get water from it or just simply switch it on.

Example Response 2:
- Thought: The current task of cut the wire from the wire roll seems needing a sharp tool to cut it off.
  - For action click, I have already tried before and failed, so not a good idea to try again.
  - For action apply, I have a scissors in my bag which may be used to cut things, a blade very sharp also useful to cut things, and a hammer that could smash. I should try all of these actions.
  - For action input, from task description it doesn't need input a string to solve the task, even though memory pad has some password hint. So not a good idea to try input action for this task.
- Actions:
  - apply(scissors, wire roll): The scissors normally can be used to cut the wire, it's common sense.
  - apply(blade, wire roll): The blade is sharp and can be used to cut things open or apart, so it may also cut the wire.
  - apply(hammer, wire roll): The hammer is heavy and can smash things, but it may also be used to get things separated. Even though less likely for currrent situation, but still worth a try."""
  


CREATIVE_SYS_REFLECTION = """You are a helpful agent to reflect on your action and environment response, and then maintain a task list with solving suggestions.
The role of this task list is that there are some tasks you currently cannot solve with the tools at hand, but you think you may need to solve them later, so write them down with some suggestions and hints for your future reference.

After analyzing your current action and the response from the environment, you should give an action to maintain the task list: <function_list>
<param_explain>
For instance, valid task list maintaining action may be: <use_example>."""


REFLECT_ACTS = {
    "update": ["update", "update(updated_feedback)", "The parameter should an updated feedback about what you newly tried but failed. The updated feedback should retain the original feedback, and add one new hindsight you got from current action", "update(The door has a keyhole and needs a key. I try apply a hammer but fails.)",],
    "new": ["new", "new(task_name, feedback)", "The first parameter should be a brief name of the new task you propose, the second parameter should be what you have to do (extract hint from environment response) to solve this task.", "new(cut the wire, I may need something sharp to cut the wire), new(open the safe, I need a 4-digit password input to open it with a hint of sigma sign beside the safe.)"],
    "delete": ["delete", "delete(index)", "If you choose delete, then the first parameter should be the index of the task in the task list that you thought you have completed or is not useful anymore.", "delete(1)"],
    "none": ["none", "none()", "If you choose none, do not give any parameter, it indicates you believe you don't need to perform any action on the task list in current step.", "none()"]
}
