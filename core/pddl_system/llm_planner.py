#!/usr/bin/env python3
"""
LLM-based PDDL Planner Module

This module uses Google's Gemini LLM to solve PDDL planning problems.
It takes a PDDL domain and problem as input and generates a valid action plan.
"""

import os
import signal
from contextlib import contextmanager
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


@contextmanager
def timeout(seconds):
    """Timeout context manager using SIGALRM"""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")

    original_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, original_handler)


class LLMPlanner:
    """
    LLM-based PDDL planner that uses Gemini to generate action plans.

    Attributes:
        model: Google Generative AI model instance
        scene_objects: Dictionary containing available objects and their capabilities
        virtualhome_domain: PDDL domain definition string
    """

    def __init__(self, model, scene_objects=None, virtualhome_domain=None):
        """
        Initialize the LLM planner.

        Args:
            model: Google Generative AI model instance
            scene_objects: Dictionary with scene object information (optional)
            virtualhome_domain: PDDL domain definition (optional)
        """
        self.model = model
        self.scene_objects = scene_objects or {}
        self.virtualhome_domain = virtualhome_domain or ""

    def solve_pddl_with_llm(self, pddl_problem, task):
        """
        Use Gemini to solve PDDL problem.

        Args:
            pddl_problem: PDDL problem string
            task: Task dictionary with 'title', 'description', 'task_id'

        Returns:
            str: PDDL solution plan

        Raises:
            RuntimeError: If LLM fails to generate valid plan after retries
        """
        print("Step 3: Solving PDDL with Gemini 1.5 Flash")

        # Get available objects and their capabilities from the scene
        capabilities = self.scene_objects.get('capabilities', {})

        # Build generic capability description for LLM
        capability_descriptions = []

        for obj_name, obj_caps in sorted(capabilities.items()):
            actions = obj_caps['actions']
            properties = obj_caps['properties']
            states = obj_caps['states']

            # Format: objectname(properties)[current_states] -> valid_actions
            props_str = ','.join(properties) if properties else ''
            states_str = ','.join(states) if states else ''
            actions_str = ', '.join(actions)

            desc = f"{obj_name}"
            if props_str:
                desc += f"({props_str})"
            if states_str:
                desc += f"[{states_str}]"
            desc += f" -> {actions_str}"

            capability_descriptions.append(desc)

        # Group objects by rooms for spatial understanding
        rooms = self.scene_objects.get('rooms', [])
        rooms_str = ', '.join(rooms) if rooms else 'none available'

        # Format capability descriptions for prompt
        capabilities_text = '\n'.join(capability_descriptions[:50])  # Limit to 50 most relevant

        solve_prompt = f"""
You are a PDDL planner for VirtualHome simulator.

TASK TO ACCOMPLISH:
{task['title']} - {task['description']}

YOUR JOB: Infer the goal state from the task description above and generate a plan to achieve it.

ENVIRONMENT:
Available rooms: {rooms_str}

AVAILABLE OBJECTS & ACTIONS:
{capabilities_text}

VALID PDDL ACTIONS (use EXACT names):
1. walk ?agent ?from-location ?to-location
   Example: (walk agent kitchen bedroom)

2. find-object ?agent ?object ?room
   Example: (find-object agent computer bedroom)

3. sit-down ?agent ?furniture
   Example: (sit-down agent chair)

4. switch-on ?agent ?appliance
   Example: (switch-on agent computer)

5. switch-off ?agent ?appliance
   Example: (switch-off agent tv)

6. touch-object ?agent ?object
   Example: (touch-object agent remote_control)

7. open-container ?agent ?container
   Example: (open-container agent fridge)

8. close-container ?agent ?container
   Example: (close-container agent fridge)

9. grab-object ?agent ?object
   Example: (grab-object agent apple)

10. put-object-in ?agent ?object ?container
    Example: (put-object-in agent apple fridge)

CRITICAL RULES:
- Use EXACT action names above (e.g., "find-object" NOT "find", "switch-on" NOT "switchon")
- ONLY use switch-on/switch-off on objects with SWITCHON/SWITCHOFF in their action list
- Objects with only TOUCH actions cannot be switched - use touch-object instead
- Check the "AVAILABLE OBJECTS & ACTIONS" list to see what each object can do

PLANNING APPROACH:
1. **Understand the task** - What is the desired end state?
2. **Identify required objects** - Which objects from the list above are needed?
3. **Proper action sequencing**:
   - Always WALK to room before finding objects there
   - Always FIND object before interacting with it
   - For sitting + switching: Find furniture, SIT, then FIND and interact with nearby objects
   - For grabbing: FIND object, GRAB, then use it (don't sit before grabbing)
   - Find containers BEFORE opening them
4. **Generate minimal plan** - Fewest actions to achieve the goal
5. **Use EXACT action names** - Match the action list exactly
6. **Use only listed objects** - No assumptions about unavailable objects

EXAMPLES OF GOAL INFERENCE:
- "Write an email" → Goal: Agent sitting at computer, computer ON
- "Put groceries in fridge" → Goal: Fridge opened, items inside, fridge closed
- "Watch TV" → Goal: Agent sitting, TV ON
- "Go to sleep" → Goal: Agent in bedroom, on bed
- "Turn on light" → Goal: Agent in room, light/appliance ON

PDDL PROBLEM (for context - goal is in the task description):
{pddl_problem}

OUTPUT FORMAT:
(:plan
  (action agent param1 param2)
  ...
)

Generate the shortest plan that achieves the goal described in the task above.
Use ONLY the exact action names listed above and objects from the available objects list.
"""

        max_retries = 3
        llm_timeout = 60  # seconds

        for attempt in range(max_retries):
            try:
                print(f"  Attempt {attempt + 1}/{max_retries}... (timeout: {llm_timeout}s)")

                with timeout(llm_timeout):
                    response = self.model.generate_content(solve_prompt)
                    pddl_solution = response.text

                if not pddl_solution or len(pddl_solution.strip()) < 10:
                    raise ValueError("LLM returned empty or invalid response")

                # Validate the plan with object capabilities
                valid, errors = self._validate_pddl_plan(pddl_solution, capabilities)

                if not valid:
                    print("  ⚠️ LLM generated invalid plan:")
                    for error in errors:
                        print(f"    - {error}")

                    if attempt < max_retries - 1:
                        print(f"  Retrying with stricter prompt...")
                        solve_prompt += f"\n\nPREVIOUS ATTEMPT HAD ERRORS:\n" + "\n".join(errors)
                        continue
                    else:
                        raise ValueError(f"LLM failed to generate valid plan after {max_retries} attempts:\n" + "\n".join(errors))

                print(f"✅ PDDL Solution validated ({len(pddl_solution)} chars)")
                print("PDDL Plan:")
                print(pddl_solution)
                break

            except TimeoutError as e:
                print(f"  ❌ Timeout: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying...")
                    continue
                else:
                    raise RuntimeError(f"LLM failed to respond after {max_retries} attempts")

            except google_exceptions.ResourceExhausted as e:
                print(f"  ❌ API quota exceeded: {e}")
                raise RuntimeError("Google API quota exceeded. Please wait and try again.")

            except google_exceptions.InvalidArgument as e:
                print(f"  ❌ Invalid API argument: {e}")
                raise RuntimeError(f"Invalid prompt format: {e}")

            except Exception as e:
                print(f"  ❌ Error: {type(e).__name__}: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying...")
                    continue
                else:
                    raise

        # Save PDDL solution to task-specific directory
        task_dir = f"Output/task_{task['task_id']}"
        os.makedirs(task_dir, exist_ok=True)
        solution_filename = os.path.join(task_dir, "pddl_solution.txt")
        try:
            with open(solution_filename, 'w') as f:
                f.write(f"Task: {task['title']} - {task['description']}\n")
                f.write("=" * 60 + "\n")
                f.write("PDDL SOLUTION:\n")
                f.write("=" * 60 + "\n")
                f.write(pddl_solution)
        except Exception as e:
            print(f"Warning: Could not save PDDL solution file: {e}")

        return pddl_solution

    def _validate_pddl_plan(self, pddl_solution, capabilities=None):
        """
        Validate LLM-generated PDDL plan with type checking.

        Args:
            pddl_solution: PDDL solution string
            capabilities: Object capabilities dict (optional for type checking)

        Returns:
            tuple: (is_valid: bool, errors: list of str)
        """
        validation_errors = []

        # Extract actions from solution
        actions = []
        for line in pddl_solution.strip().split('\n'):
            line = line.strip()
            if line.startswith('(') and not line.startswith('(:plan'):
                if line.endswith(')'):
                    line = line[1:-1]
                    parts = line.split()
                    if parts:
                        actions.append((parts[0], parts[1:]))

        if not actions:
            validation_errors.append("No actions found in plan")
            return False, validation_errors

        # Valid actions from domain
        valid_actions = {
            'walk': 3,
            'find-object': 3,
            'sit-down': 2,
            'switch-on': 2,
            'switch-off': 2,
            'touch-object': 2,
            'open-container': 2,
            'close-container': 2,
            'grab-object': 2,
            'put-object-in': 3
        }

        # Build capabilities lookup if provided
        switchable_objects = set()
        grabbable_objects = set()
        if capabilities:
            for obj_name, obj_caps in capabilities.items():
                actions_list = obj_caps.get('actions', [])
                if 'SWITCHON' in actions_list or 'SWITCHOFF' in actions_list:
                    switchable_objects.add(obj_name)
                if 'GRAB' in actions_list:
                    grabbable_objects.add(obj_name)

        # Validate each action
        for i, (action_name, params) in enumerate(actions):
            action_name_lower = action_name.lower()

            if action_name_lower not in valid_actions:
                validation_errors.append(
                    f"Action {i+1}: Unknown action '{action_name}'"
                )
                continue

            expected_params = valid_actions[action_name_lower]
            if len(params) != expected_params:
                validation_errors.append(
                    f"Action {i+1}: '{action_name}' expects {expected_params} parameters, got {len(params)}"
                )
                continue

            # Type checking if capabilities available
            if capabilities:
                if action_name_lower in ['switch-on', 'switch-off']:
                    # Second param should be switchable object
                    if len(params) >= 2:
                        obj = params[1]
                        if obj not in switchable_objects and obj != 'agent':
                            validation_errors.append(
                                f"Action {i+1}: '{obj}' cannot be switched on/off (not a switchable appliance). Use TOUCH instead."
                            )

                elif action_name_lower == 'grab-object':
                    # Second param should be grabbable
                    if len(params) >= 2:
                        obj = params[1]
                        if obj not in grabbable_objects and obj != 'agent':
                            validation_errors.append(
                                f"Action {i+1}: '{obj}' is not grabbable"
                            )

        if validation_errors:
            return False, validation_errors

        return True, []
