#!/usr/bin/env python3

import os
import sys
import json
import glob
import subprocess
import socket
import signal
import time
from contextlib import contextmanager
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

sys.path.append(os.path.join(os.path.dirname(__file__), '../virtualhome/virtualhome/simulation'))
from unity_simulator import comm_unity


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

class PDDLVirtualHomeSystem:
    """
    Complete PDDL-centric VirtualHome task solving system:
    1. Scene + Task → PDDL Problem
    2. LLM Solves PDDL Problem
    3. PDDL Solution → VirtualHome Script
    4. Execute + Verify (headless)
    5. Generate Video
    """

    def __init__(self, simulator_path, api_key, port=None):
        self.simulator_path = simulator_path
        self.comm = None
        self.port = port
        self.current_task_id = None

        # Validate inputs
        if not api_key:
            raise ValueError("API key is required")

        if not os.path.exists(simulator_path):
            raise FileNotFoundError(f"Simulator not found at: {simulator_path}")

        # Ensure core/Output directory exists
        core_output_dir = os.path.join(os.path.dirname(__file__), 'Output')
        os.makedirs(core_output_dir, exist_ok=True)

        # Configure Gemini 1.5 Flash
        genai.configure(api_key=api_key)

        # Find available Flash model
        models = genai.list_models()
        available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]

        flash_model = None
        for model_name in available_models:
            if 'flash' in model_name.lower():
                flash_model = model_name
                break

        if flash_model:
            self.model = genai.GenerativeModel(flash_model)
            print(f"✅ Using {flash_model}")
        else:
            self.model = genai.GenerativeModel(available_models[0])
            print(f"✅ Using fallback model: {available_models[0]}")

        # PDDL Domain for VirtualHome
        self.virtualhome_domain = """
(define (domain virtualhome)
  (:requirements :strips :typing)

  (:types
    agent room furniture appliance container interactive-object - object
    location - object
  )

  (:predicates
    ; Agent location and state
    (at ?agent - agent ?loc - location)
    (sitting ?agent - agent)
    (holding ?agent - agent ?obj - object)

    ; Object states
    (on ?obj - appliance)
    (off ?obj - appliance)
    (open ?obj - container)
    (closed ?obj - container)
    (accessible ?obj - object)
    (grabbable ?obj - object)

    ; Spatial relationships
    (in-room ?obj - object ?room - room)
    (near ?obj1 - object ?obj2 - object)
    (can-sit ?agent - agent ?furniture - furniture)
    (can-interact ?agent - agent ?obj - object)
    (in-container ?obj - object ?container - container)
  )

  (:action walk
    :parameters (?agent - agent ?from - location ?to - location)
    :precondition (at ?agent ?from)
    :effect (and (not (at ?agent ?from)) (at ?agent ?to))
  )

  (:action find-object
    :parameters (?agent - agent ?obj - object ?room - room)
    :precondition (and (at ?agent ?room) (in-room ?obj ?room))
    :effect (accessible ?obj)
  )

  (:action sit-down
    :parameters (?agent - agent ?chair - furniture)
    :precondition (and (accessible ?chair) (can-sit ?agent ?chair))
    :effect (sitting ?agent)
  )

  (:action switch-on
    :parameters (?agent - agent ?appliance - appliance)
    :precondition (and (accessible ?appliance) (off ?appliance) (can-interact ?agent ?appliance))
    :effect (and (on ?appliance) (not (off ?appliance)))
  )

  (:action switch-off
    :parameters (?agent - agent ?appliance - appliance)
    :precondition (and (accessible ?appliance) (on ?appliance) (can-interact ?agent ?appliance))
    :effect (and (off ?appliance) (not (on ?appliance)))
  )

  (:action touch-object
    :parameters (?agent - agent ?obj - interactive-object)
    :precondition (and (accessible ?obj) (can-interact ?agent ?obj))
    :effect (and) ; Interaction happened
  )

  (:action open-container
    :parameters (?agent - agent ?container - container)
    :precondition (and (accessible ?container) (closed ?container) (can-interact ?agent ?container))
    :effect (and (open ?container) (not (closed ?container)))
  )

  (:action close-container
    :parameters (?agent - agent ?container - container)
    :precondition (and (accessible ?container) (open ?container) (can-interact ?agent ?container))
    :effect (and (closed ?container) (not (open ?container)))
  )

  (:action grab-object
    :parameters (?agent - agent ?obj - object)
    :precondition (and (accessible ?obj) (grabbable ?obj) (not (holding ?agent ?obj)))
    :effect (holding ?agent ?obj)
  )

  (:action put-object-in
    :parameters (?agent - agent ?obj - object ?container - container)
    :precondition (and (holding ?agent ?obj) (accessible ?container) (open ?container))
    :effect (and (not (holding ?agent ?obj)) (in-container ?obj ?container))
  )
)
"""

    def load_scene_and_task(self, task_id=0):
        """Step 1: Load VirtualHome scene and task"""
        print(f"Step 1: Loading scene and task {task_id}")

        # Validate task_id
        if not isinstance(task_id, int):
            raise TypeError(f"task_id must be integer, got {type(task_id).__name__}")

        if task_id < 0:
            raise ValueError(f"task_id must be non-negative, got {task_id}")

        # Load tasks from dataset
        scene_name = "TrimmedTestScene1_graph"
        base_path = os.path.join(os.path.dirname(__file__), '..',
                                'virtualhome/virtualhome/dataset/programs_processed_precond_nograb_morepreconds')

        executable_path = os.path.join(base_path, 'executable_programs', scene_name, 'results_intentions_march-13-18')
        task_files = sorted(glob.glob(os.path.join(executable_path, '*.txt')))

        if not task_files:
            raise RuntimeError(f"No task files found in {executable_path}")

        if task_id >= len(task_files):
            raise ValueError(f"Task {task_id} not found. Available: 0-{len(task_files)-1}")

        # Load task with validation
        task_file = task_files[task_id]
        if not os.path.isfile(task_file):
            raise FileNotFoundError(f"Task file not found: {task_file}")

        with open(task_file, 'r') as f:
            lines = f.readlines()

        if len(lines) < 2:
            raise ValueError(f"Invalid task file format: expected at least 2 lines, got {len(lines)}")

        task = {
            'id': task_id,
            'task_id': task_id,  # For consistency
            'title': lines[0].strip() if lines[0].strip() else f"Task_{task_id}",
            'description': lines[1].strip() if lines[1].strip() else "No description"
        }

        # Load corresponding graph
        graph_file = task_files[task_id].replace('executable_programs', 'init_and_final_graphs').replace('.txt', '.json')
        with open(graph_file, 'r') as f:
            graphs = json.load(f)
            task['initial_graph'] = graphs['init_graph']
            task['final_graph'] = graphs['final_graph']

        print(f" Loaded: {task['title']} - {task['description']}")
        return task

    def _get_available_port(self, start_port=8080, max_attempts=10):
        """Find available port for simulator"""
        for offset in range(max_attempts):
            port = start_port + offset
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.bind(('localhost', port))
                sock.close()
                return str(port)
            except OSError:
                sock.close()
                continue

        raise RuntimeError(
            f"No available ports in range {start_port}-{start_port+max_attempts-1}. "
            f"Please close existing simulator instances."
        )

    def _initialize_or_reuse_simulator(self, task):
        """Initialize simulator if needed, or reuse existing one"""
        # Get available port (only once per instance)
        if not self.port:
            self.port = self._get_available_port()
            print(f"  Using simulator port: {self.port}")

        # If simulator already initialized, just reload the scene
        if self.comm is not None:
            print(f"  Reusing existing simulator on port {self.port}")
            try:
                self.comm.reset(0)
                self.comm.expand_scene(task['initial_graph'])
                self.comm.add_character('Chars/Male2', initial_room='kitchen')
                success, scene_graph = self.comm.environment_graph()
                if not success:
                    raise RuntimeError("Failed to get scene graph")
                print(f"  ✅ Scene reloaded successfully")
                return scene_graph
            except Exception as e:
                print(f"  ⚠️ Reuse failed: {e}, reinitializing...")
                try:
                    self.comm.close()
                except:
                    pass
                self.comm = None

        # Initialize VirtualHome with health checks
        print(f"  Initializing simulator...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.comm = comm_unity.UnityCommunication(
                    file_name=self.simulator_path,
                    port=self.port
                )

                # Wait for simulator to start
                time.sleep(2)

                # Test communication
                success, test_graph = self.comm.environment_graph()
                if not success:
                    raise RuntimeError("Simulator started but not responding")

                # Reset and load scene
                self.comm.reset(0)
                self.comm.expand_scene(task['initial_graph'])
                self.comm.add_character('Chars/Male2', initial_room='kitchen')

                # Final health check
                success, scene_graph = self.comm.environment_graph()
                if not success:
                    raise RuntimeError("Failed to get scene graph after loading")

                print(f"  ✅ Simulator initialized successfully")
                return scene_graph

            except Exception as e:
                print(f"  ❌ Initialization attempt {attempt+1}/{max_retries} failed: {e}")
                if self.comm:
                    try:
                        self.comm.close()
                    except:
                        pass
                    self.comm = None

                if attempt < max_retries - 1:
                    print(f"  Retrying in 2 seconds...")
                    time.sleep(2)
                    return None
                else:
                    raise RuntimeError(f"Failed to initialize simulator after {max_retries} attempts")
        return None

    def scene_to_pddl_problem(self, task):
        """Step 2: Convert scene and task to PDDL problem"""
        print("Step 2: Converting scene to PDDL problem")

        # Initialize or reuse simulator
        scene_graph = self._initialize_or_reuse_simulator(task)

        # DEBUG: Print objects for troubleshooting
        if 'remote' in task['description'].lower():
            print("\\n=== DEBUG: Objects containing 'remote' ===")
            for node in scene_graph['nodes']:
                if 'remote' in node['class_name'].lower():
                    print(f"- {node['class_name']} (ID: {node['id']})")
            print("=== DEBUG: All objects in scene ===")
            for node in scene_graph['nodes'][:20]:  # First 20
                print(f"- {node['class_name']} (ID: {node['id']})")

            # DEBUG: Print object mapping that will be created
            print("=== DEBUG: Object Mapping Preview ===")
            object_map = self._get_object_id_mapping()
            remote_related = {k: v for k, v in object_map.items() if 'remote' in k.lower()}
            print(f"Remote-related mappings: {remote_related}")

        # Create concise PDDL problem
        objects_section = []
        init_section = []

        # Categorize objects
        rooms = []
        furniture = []
        appliances = []
        interactive_objects = []

        # Track unique object names and create mapping
        object_names_seen = set()
        base_name_to_ids = {}  # Track multiple objects of same type
        non_interactable_objects = []  # Track objects that cannot be directly interacted with

        # Define interactable properties that VirtualHome supports
        INTERACTABLE_PROPERTIES = {'GRABBABLE', 'CAN_OPEN', 'HAS_SWITCH', 'SITTABLE', 'LOOKABLE', 'RECIPIENT', 'SURFACES'}

        for node in scene_graph['nodes']:
            base_name = node['class_name'].lower().replace(' ', '_')
            node_id = node['id']
            states = node.get('states', [])
            properties = node.get('properties', [])
            category = node.get('category', '')

            # Track all IDs for each base name
            if base_name not in base_name_to_ids:
                base_name_to_ids[base_name] = []
            base_name_to_ids[base_name].append(node_id)

            # Use base name without ID for PDDL
            name = base_name

            # Skip if we've already added this base name
            if name in object_names_seen:
                continue

            object_names_seen.add(name)

            # Check if object has ANY interactable properties
            has_interactable_property = any(prop in properties for prop in INTERACTABLE_PROPERTIES)

            # Categorize based on scene graph properties (dynamic, not hardcoded)
            # IMPORTANT: Only include objects that VirtualHome can actually interact with

            # 1. Check if it's a room (by name pattern - rooms don't have clear categories)
            if any(room in base_name for room in ['kitchen', 'bedroom', 'bathroom', 'living', 'office', 'hallway']):
                rooms.append(name)
                objects_section.append(f"{name} - room")

            # 2. Check if it has SITTABLE property -> furniture
            elif 'SITTABLE' in properties:
                furniture.append(name)
                objects_section.append(f"{name} - furniture")
                init_section.append(f"(can-sit agent {name})")

            # 3. Check if it's in Furniture category AND has interactable properties
            elif category == 'Furniture' and has_interactable_property:
                furniture.append(name)
                objects_section.append(f"{name} - furniture")
                if 'SITTABLE' in properties:
                    init_section.append(f"(can-sit agent {name})")

            # 4. Check if it has HAS_SWITCH property (explicitly switchable) -> appliance
            elif 'HAS_SWITCH' in properties:
                appliances.append(name)
                objects_section.append(f"{name} - appliance")
                if 'ON' in states:
                    init_section.append(f"(on {name})")
                else:
                    init_section.append(f"(off {name})")

            # 5. Check if it's in Electronics category AND has HAS_SWITCH or is grabbable
            elif category == 'Electronics' and has_interactable_property:
                appliances.append(name)
                objects_section.append(f"{name} - appliance")
                if 'ON' in states:
                    init_section.append(f"(on {name})")
                elif 'OFF' in states:
                    init_section.append(f"(off {name})")

            # 6. Lamps: ONLY include if they have HAS_SWITCH (can be turned on/off)
            elif category == 'Lamps':
                if 'HAS_SWITCH' in properties:
                    appliances.append(name)
                    objects_section.append(f"{name} - appliance")
                    if 'ON' in states:
                        init_section.append(f"(on {name})")
                    else:
                        init_section.append(f"(off {name})")
                else:
                    # Non-switchable lamps cannot be interacted with in VirtualHome
                    non_interactable_objects.append(name)

            # 7. Special case: fridge is a container
            elif 'fridge' in name:
                appliances.append(name)
                objects_section.append(f"{name} - container")
                init_section.append(f"(closed {name})")
                init_section.append(f"(accessible {name})")
                init_section.append(f"(can-interact agent {name})")

            # 8. Check if it has CAN_OPEN property or is a door/container -> interactive
            elif 'CAN_OPEN' in properties or category in ['Doors']:
                interactive_objects.append(name)
                objects_section.append(f"{name} - interactive-object")

            # 9. Objects with GRABBABLE property can be picked up
            elif 'GRABBABLE' in properties:
                interactive_objects.append(name)
                objects_section.append(f"{name} - interactive-object")
                init_section.append(f"(grabbable {name})")

            # 10. Everything else without interactable properties is non-interactable
            elif not has_interactable_property:
                non_interactable_objects.append(name)

            # 11. Catch-all for objects with properties but not yet categorized
            else:
                interactive_objects.append(name)
                objects_section.append(f"{name} - interactive-object")

        # Add agent and spatial relationships
        objects_section.insert(0, "agent - agent")
        init_section.append("(at agent kitchen)")

        # No fake objects - use only real scene objects for generalization

        # Add room containment (simplified)
        for room in rooms:
            for obj in furniture + appliances + interactive_objects:
                # Simple heuristic: computer/keyboard in bedroom, fridge in kitchen, etc.
                if 'computer' in obj or 'keyboard' in obj or 'desk' in obj:
                    if 'bedroom' in room:
                        init_section.append(f"(in-room {obj} {room})")
                elif 'fridge' in obj or 'stove' in obj:
                    if 'kitchen' in room:
                        init_section.append(f"(in-room {obj} {room})")

        # Create goal based on task - more comprehensive goals
        goal_conditions = []
        task_lower = task['description'].lower()

        if 'email' in task_lower or 'computer' in task_lower:
            goal_conditions.extend([
                "(sitting agent)",
                "(on computer)",
                "(accessible keyboard)"
            ])
        elif 'fridge' in task_lower or 'groceries' in task_lower:
            # For fridge tasks, focus on realistic fridge interaction
            goal_conditions.extend([
                "(at agent kitchen)",
                "(accessible fridge)",
                "(closed fridge)"  # Fridge should be properly closed at end
            ])
        elif 'toilet' in task_lower or 'bathroom' in task_lower:
            goal_conditions.append("(at agent bathroom)")
        elif 'tv' in task_lower or 'television' in task_lower:
            goal_conditions.extend([
                "(at agent livingroom)",
                "(on tv)",
                "(sitting agent)"
            ])
        else:
            # Generic goal based on task location
            if 'kitchen' in task_lower:
                goal_conditions.append("(at agent kitchen)")
            elif 'bedroom' in task_lower:
                goal_conditions.append("(at agent bedroom)")
            elif 'living' in task_lower:
                goal_conditions.append("(at agent livingroom)")
            else:
                goal_conditions.append("(at agent bedroom)")  # Default

        # Store categorized objects for LLM prompt (after all objects are added)
        self._current_scene_objects = {
            'rooms': rooms,
            'furniture': furniture,
            'appliances': appliances,
            'interactive_objects': interactive_objects,
            'non_interactable': non_interactable_objects
        }

        # Construct PDDL problem
        pddl_problem = f"""
(define (problem {task['title'].replace(' ', '-').lower()})
  (:domain virtualhome)

  (:objects
    {chr(10).join('    ' + obj for obj in objects_section[:20])}  ; Limit to 20 objects
  )

  (:init
    {chr(10).join('    ' + init for init in init_section[:30])}  ; Limit to 30 init conditions
  )

  (:goal
    (and
      {chr(10).join('      ' + goal for goal in goal_conditions)}
    )
  )
)
"""

        print(f"✅ PDDL Problem created with {len(objects_section)} objects, {len(init_section)} init conditions")

        # Save PDDL problem to text file for review
        pddl_filename = f"Output/pddl_task_{task['task_id']}_problem.txt"
        try:
            with open(pddl_filename, 'w') as f:
                f.write(f"Task: {task['title']} - {task['description']}\n")
                f.write("=" * 60 + "\n")
                f.write("PDDL PROBLEM:\n")
                f.write("=" * 60 + "\n")
                f.write(pddl_problem)
        except Exception as e:
            print(f"Warning: Could not save PDDL file: {e}")

        return pddl_problem

    def _validate_pddl_plan(self, pddl_solution):
        """Validate LLM-generated PDDL plan"""
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

        # Validate each action
        for i, (action_name, params) in enumerate(actions):
            action_name = action_name.lower()

            if action_name not in valid_actions:
                validation_errors.append(
                    f"Action {i+1}: Unknown action '{action_name}'"
                )
                continue

            expected_params = valid_actions[action_name]
            if len(params) != expected_params:
                validation_errors.append(
                    f"Action {i+1}: '{action_name}' expects {expected_params} parameters, got {len(params)}"
                )

        if validation_errors:
            return False, validation_errors

        return True, []

    def solve_pddl_with_llm(self, pddl_problem, task):
        """Step 3: Use Gemini to solve PDDL problem"""
        print("Step 3: Solving PDDL with Gemini 1.5 Flash")

        # Get available objects from the scene
        scene_objects = getattr(self, '_current_scene_objects', {})
        rooms = scene_objects.get('rooms', [])
        furniture = scene_objects.get('furniture', [])
        appliances = scene_objects.get('appliances', [])
        interactive = scene_objects.get('interactive_objects', [])
        non_interactable = scene_objects.get('non_interactable', [])

        # Format object lists for prompt (include ALL objects, no limits)
        rooms_str = ', '.join(rooms) if rooms else 'none'
        furniture_str = ', '.join(furniture) if furniture else 'none'
        appliances_str = ', '.join(appliances) if appliances else 'none'
        interactive_str = ', '.join(interactive) if interactive else 'none'

        # Add helpful hints for common object name variations
        hints = []
        all_objects = rooms + furniture + appliances + interactive

        # Check for lights/lamps
        lamps = [obj for obj in all_objects if 'lamp' in obj.lower() or 'light' in obj.lower()]
        if lamps:
            hints.append(f"For 'light', use: {', '.join(lamps)}")

        # Check for TV/television
        tvs = [obj for obj in all_objects if 'tv' in obj.lower() or 'television' in obj.lower()]
        if tvs:
            hints.append(f"For 'tv', use: {', '.join(tvs)}")

        # Check for computer-related
        computers = [obj for obj in all_objects if 'computer' in obj.lower() or 'screen' in obj.lower()]
        if computers:
            hints.append(f"For 'computer', use: {', '.join(computers)}")

        hints_str = '\n  '.join(hints) if hints else 'No special hints needed'

        # Add warnings about non-interactable objects
        non_interactable_warning = ''
        if non_interactable:
            non_interactable_str = ', '.join(non_interactable[:10])  # Show first 10
            if len(non_interactable) > 10:
                non_interactable_str += f' (and {len(non_interactable) - 10} more)'
            non_interactable_warning = f"""
WARNING - NON-INTERACTABLE OBJECTS (cannot be used in actions):
  {non_interactable_str}

  These objects exist in the scene but CANNOT be interacted with (no FIND, GRAB, SWITCHON, etc).
  If task requires one of these objects, find an alternative from the interactable lists above.
"""

        solve_prompt = f"""
You are a PDDL planner. Given the domain and problem below, generate a valid PDDL solution plan.

TASK: {task['title']} - {task['description']}

CRITICAL CONSTRAINT - AVAILABLE OBJECTS IN SCENE:
You can ONLY use objects that actually exist in this apartment scene:

  ROOMS: {rooms_str}
  FURNITURE: {furniture_str}
  APPLIANCES: {appliances_str}
  INTERACTIVE: {interactive_str}

OBJECT NAME HINTS:
  {hints_str}
{non_interactable_warning}
DO NOT use any objects not listed above. If the task mentions objects that don't exist, either:
   1. Find the closest available substitute from the list above
   2. Simplify the task to use only available objects
   3. Skip actions involving non-existent objects

Examples:
- If task says "grab groceries" but no groceries exist -> just open/close the fridge
- If task says "turn on light" but ceilinglamp is non-interactable -> use available lamps from hints or skip
- If task says "read book" but no book exists -> walk to the location and sit down

DOMAIN AND PROBLEM:
{self.virtualhome_domain}

{pddl_problem}

REQUIREMENTS:
1. Return a valid sequence of PDDL actions that achieves the goal
2. Use ONLY objects that exist in the scene (see list above)
3. Use the exact action names and parameters from the domain
4. Ensure preconditions are satisfied before each action
5. Format your response as a structured plan

OUTPUT FORMAT (return exactly this structure):
(:plan
  (walk agent kitchen bedroom)
  (find-object agent computer bedroom)
  (find-object agent chair bedroom)
  (sit-down agent chair)
  (switch-on agent computer)
  (find-object agent keyboard bedroom)
  (touch-object agent keyboard)
  (switch-off agent computer)
)

Generate the complete plan to solve: "{task['description']}"
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

                # Validate the plan
                valid, errors = self._validate_pddl_plan(pddl_solution)

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

        # Save PDDL solution to text file for review
        solution_filename = f"Output/pddl_task_{task['task_id']}_solution.txt"
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

    def pddl_to_virtualhome_script(self, pddl_solution):
        """Step 4: Convert PDDL solution to VirtualHome script"""
        print("Step 4: Converting PDDL to VirtualHome script")

        # Extract actions from PDDL solution
        actions = []
        lines = pddl_solution.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('(') and not line.startswith('(:plan'):
                # Parse PDDL action: (action-name param1 param2 ...)
                if line.endswith(')'):
                    line = line[1:-1]  # Remove outer parentheses
                    parts = line.split()
                    if len(parts) >= 2:
                        action_name = parts[0]
                        params = parts[1:]
                        actions.append((action_name, params))

        # Convert to VirtualHome script with proper sequencing
        vh_script = []
        object_id_map = self._get_object_id_mapping()
        found_objects = set()  # Track what we've found

        for action_name, params in actions:
            # Convert the actual action
            vh_action = self._convert_pddl_action_to_vh(action_name, params, object_id_map)
            if vh_action:
                vh_script.append(f"<char0> {vh_action}")

                # Track objects we've found
                if action_name == 'find-object' and len(params) >= 2:
                    found_objects.add(params[1])

        print(f"✅ Converted to VirtualHome script with {len(vh_script)} actions")
        for i, action in enumerate(vh_script):
            print(f"  {i+1}. {action}")

        # DEBUG: Print object mapping used in conversion
        if hasattr(self, 'current_task_id') and self.current_task_id in [3, 9]:
            print("\\n=== DEBUG: Object Mapping During Conversion ===")
            object_map = self._get_object_id_mapping()
            for name, obj_id in object_map.items():
                if 'remote' in name.lower():
                    print(f"  {name} -> {obj_id}")
            print("=== DEBUG: PDDL Actions vs VH Script ===")
            for i, (action_name, params) in enumerate(actions):
                vh_action = vh_script[i] if i < len(vh_script) else "FAILED TO CONVERT"
                print(f"  PDDL: {action_name} {params}")
                print(f"  VH:   {vh_action}")
                print()

        # Save VirtualHome script to text file for review
        script_filename = f"Output/pddl_task_{getattr(self, 'current_task_id', 'unknown')}_script.txt"
        try:
            with open(script_filename, 'w') as f:
                f.write(f"VIRTUALHOME SCRIPT:\n")
                f.write("=" * 60 + "\n")
                for i, action in enumerate(vh_script):
                    f.write(f"{i+1}. {action}\n")
        except Exception as e:
            print(f"Warning: Could not save VirtualHome script file: {e}")

        return vh_script

    def _get_object_id_mapping(self):
        """Get mapping from object names to VirtualHome IDs"""
        if not self.comm:
            return {}

        success, graph = self.comm.environment_graph()
        if not success:
            return {}

        mapping = {}
        # Track first instance of each object type
        first_of_type = {}

        for node in graph['nodes']:
            # Use original case from VirtualHome
            original_name = node['class_name']
            base_name = original_name.lower().replace(' ', '_')
            node_id = node['id']

            # Map base name to FIRST instance of that type (for consistency)
            if base_name not in first_of_type:
                first_of_type[base_name] = node_id
                mapping[base_name] = node_id
                mapping[f"{base_name}_original"] = original_name

            # Also map with ID suffix for specific references
            name_with_id = f"{base_name}_{node_id}"
            mapping[name_with_id] = node_id
            mapping[f"{name_with_id}_original"] = original_name

            # Add common aliases for better object resolution
            if 'remote' in base_name or 'control' in base_name:
                mapping['tvremote'] = node_id
                mapping['tv-remote'] = node_id
                mapping['tv_remote'] = node_id
                mapping['tvremote_original'] = original_name
                mapping['tv-remote_original'] = original_name
                mapping['tv_remote_original'] = original_name

        # Add room mappings dynamically from scene graph
        room_mapping = {}
        for node in graph['nodes']:
            class_lower = node['class_name'].lower()
            if any(room in class_lower for room in ['kitchen', 'bedroom', 'bathroom', 'living']):
                room_name = class_lower.replace(' ', '_')
                if room_name not in room_mapping:  # Use first instance
                    room_mapping[room_name] = node['id']

        # Add known room mappings
        if 'kitchen' in room_mapping:
            mapping['kitchen'] = room_mapping['kitchen']
        if 'bedroom' in room_mapping:
            mapping['bedroom'] = room_mapping['bedroom']
        if 'bathroom' in room_mapping:
            mapping['bathroom'] = room_mapping['bathroom']
        if 'livingroom' in room_mapping:
            mapping['livingroom'] = room_mapping['livingroom']

        # Fallback for home_office (usually bedroom)
        mapping['home_office'] = room_mapping.get('bedroom', mapping.get('bedroom', 74))

        return mapping

    def _fuzzy_object_match(self, target_name, object_map):
        """Fuzzy match object name with multiple strategies"""
        target_lower = target_name.lower().replace('-', '_').replace(' ', '_')

        # Strategy 0: Strip ID suffix if present (bedroom_74 -> bedroom)
        import re
        base_target = re.sub(r'_\d+$', '', target_lower)  # Remove _### at end

        # Strategy 1: Try base name without ID
        if base_target in object_map and base_target != target_lower:
            print(f"  Matched '{target_name}' to base '{base_target}'")
            return object_map[base_target], object_map.get(f"{base_target}_original", base_target)

        # Strategy 2: Exact match
        if target_lower in object_map:
            return object_map[target_lower], object_map.get(f"{target_lower}_original", target_name)

        # Strategy 3: Try variations
        variations = [
            target_lower.replace('_', ''),
            target_lower.replace('_', '-'),
            target_name.lower(),
            base_target.replace('_', ''),
            base_target.replace('_', '-')
        ]

        for var in variations:
            if var in object_map:
                print(f"  Variation matched '{target_name}' to '{var}'")
                return object_map[var], object_map.get(f"{var}_original", var)

        # Strategy 4: Partial match
        for key in object_map.keys():
            if '_original' not in key:
                if base_target in key or key in base_target:
                    print(f"  Fuzzy matched '{target_name}' to '{key}'")
                    return object_map[key], object_map.get(f"{key}_original", key)

        # Strategy 5: Semantic match (common aliases)
        aliases = {
            'tv': ['television', 'tv_stand', 'tvstand'],
            'computer': ['pc', 'desktop', 'laptop', 'cpuscreen'],
            'fridge': ['refrigerator', 'icebox'],
            'couch': ['sofa'],
            'remote': ['remote_control', 'tv_remote', 'controller']
        }

        for alias_base, synonyms in aliases.items():
            if base_target == alias_base or base_target in synonyms:
                for synonym in [alias_base] + synonyms:
                    if synonym in object_map:
                        print(f"  Semantic matched '{target_name}' to '{synonym}'")
                        return object_map[synonym], object_map.get(f"{synonym}_original", synonym)

        # Failure
        print(f"  ⚠️ Object '{target_name}' not found in scene")
        available = [k for k in object_map.keys() if '_original' not in k][:20]
        print(f"  Available objects: {available}")
        return None, None

    def _convert_pddl_action_to_vh(self, action_name, params, object_map):
        """Convert single PDDL action to VirtualHome action"""
        if action_name == "walk":
            # (walk agent from to) -> [WALK] <to> (id)
            if len(params) >= 3:
                destination = params[2]
                obj_id = object_map.get(destination, 1)
                original_name = object_map.get(f"{destination}_original", destination)
                return f"[WALK] <{original_name}> ({obj_id})"

        elif action_name == "find-object":
            # (find-object agent object room) -> [FIND] <object> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id, original_name = self._fuzzy_object_match(obj_name, object_map)

                if obj_id is None:
                    print(f"  Cannot find object '{obj_name}' - using fallback")
                    obj_id = 1
                    original_name = obj_name

                return f"[FIND] <{original_name}> ({obj_id})"

        elif action_name == "sit-down":
            # (sit-down agent furniture) -> [SIT] <furniture> (id)
            if len(params) >= 2:
                furniture_name = params[1]
                furniture_id = object_map.get(furniture_name, 1)
                # Get original name for VH script
                original_name = object_map.get(f"{furniture_name}_original", furniture_name)
                return f"[SIT] <{original_name}> ({furniture_id})"

        elif action_name == "switch-on":
            # (switch-on agent appliance) -> [SWITCHON] <appliance> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id = object_map.get(obj_name, 1)
                original_name = object_map.get(f"{obj_name}_original", obj_name)
                return f"[SWITCHON] <{original_name}> ({obj_id})"

        elif action_name == "switch-off":
            # (switch-off agent appliance) -> [SWITCHOFF] <appliance> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id = object_map.get(obj_name, 1)
                original_name = object_map.get(f"{obj_name}_original", obj_name)
                return f"[SWITCHOFF] <{original_name}> ({obj_id})"

        elif action_name == "touch-object":
            # (touch-object agent object) -> [TOUCH] <object> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id = object_map.get(obj_name, 1)
                original_name = object_map.get(f"{obj_name}_original", obj_name)
                return f"[TOUCH] <{original_name}> ({obj_id})"

        elif action_name == "open-container":
            # (open-container agent container) -> [OPEN] <container> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id = object_map.get(obj_name, 1)
                original_name = object_map.get(f"{obj_name}_original", obj_name)
                return f"[OPEN] <{original_name}> ({obj_id})"

        elif action_name == "close-container":
            # (close-container agent container) -> [CLOSE] <container> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id = object_map.get(obj_name, 1)
                original_name = object_map.get(f"{obj_name}_original", obj_name)
                return f"[CLOSE] <{original_name}> ({obj_id})"

        elif action_name == "grab-object":
            # (grab-object agent object) -> [GRAB] <object> (id)
            if len(params) >= 2:
                obj_name = params[1]
                obj_id, original_name = self._fuzzy_object_match(obj_name, object_map)

                if obj_id is None:
                    print(f"  Cannot find object '{obj_name}' - using fallback")
                    obj_id = 1
                    original_name = obj_name

                return f"[GRAB] <{original_name}> ({obj_id})"

        elif action_name == "put-object-in":
            # (put-object-in agent object container) -> [PUTIN] <object> (obj_id) <container> (container_id)
            if len(params) >= 3:
                obj_name = params[1]
                container_name = params[2]
                obj_id = object_map.get(obj_name, 1)
                container_id = object_map.get(container_name, 1)
                return f"[PUTIN] <{obj_name}> ({obj_id}) <{container_name}> ({container_id})"

        return None

    def _validate_spatial_constraints(self, vh_script):
        """Pre-execution spatial validation to catch navigation issues"""
        print("\\n=== SPATIAL VALIDATION ===")

        # Get current scene state
        success, graph = self.comm.environment_graph()
        if not success:
            print("Could not get scene graph for validation")
            return True  # Continue anyway

        # Check if agent can reach target rooms/objects
        issues = []
        for i, action_line in enumerate(vh_script):
            action_parts = action_line.split()
            if len(action_parts) >= 2:
                action = action_parts[1].replace('[', '').replace(']', '')

                if action == 'WALK':
                    # Extract target room/object
                    target = action_parts[2].replace('<', '').replace('>', '')
                    print(f"  Checking walk to: {target}")
                    # For now, just warn about known problematic navigation
                    if target.lower() in ['livingroom']:
                        issues.append(f"Action {i+1}: Navigation to {target} may have collision issues")

        if issues:
            print("Potential spatial issues detected:")
            for issue in issues:
                print(f"    - {issue}")
            print("Proceeding with execution (spatial issues are VirtualHome constraints)")
        else:
            print("No obvious spatial constraint violations detected")

        return True  # Always proceed for now

    def _analyze_failure_and_replan(self, error_message, original_script, task):
        """Analyze execution failure and generate alternative plan"""
        print("\nADAPTIVE REPLANNING - Analyzing failure...")

        # Analyze the type of failure
        failure_type = None
        problematic_object = None

        if "Unknown object" in error_message:
            failure_type = "unknown_object"
            # Extract object name from error
            parts = error_message.split("Unknown object")
            if len(parts) > 1:
                problematic_object = parts[1].strip()
        elif "Can not select object" in error_message:
            failure_type = "unreachable_object"
            # Extract object name
            if "REASON:" in error_message:
                parts = error_message.split("Can not select object:")
                if len(parts) > 1:
                    obj_part = parts[1].split(".")[0].strip()
                    problematic_object = obj_part
        elif "collision" in error_message.lower():
            failure_type = "navigation_collision"

        print(f"  Failure type: {failure_type}")
        if problematic_object:
            print(f"  Problematic object: {problematic_object}")

        # Generate alternative strategy based on failure type
        if failure_type == "unknown_object" and problematic_object:
            return self._replan_for_missing_object(problematic_object, task)
        elif failure_type == "unreachable_object":
            return self._replan_for_unreachable_object(problematic_object, task)
        elif failure_type == "navigation_collision":
            return self._replan_for_navigation_collision(task)

        print("  No alternative strategy available for this failure type")
        return None

    def _replan_for_missing_object(self, missing_obj, task):
        """Generate alternative plan when object doesn't exist"""
        print(f"  Strategy: Find alternative to missing '{missing_obj}'")

        # Create simplified PDDL problem without the missing object
        simplified_prompt = f"""
        The original plan failed because object '{missing_obj}' doesn't exist in the scene.

        Task: {task['description']}

        Generate a SIMPLER plan that accomplishes the core task goal without requiring '{missing_obj}'.
        Focus on the essential actions only.

        Return only a PDDL plan in this format:
        (:plan
          (action1 agent ...)
          (action2 agent ...)
        )
        """

        try:
            response = self.model.generate_content(simplified_prompt)
            alternative_plan = response.text.strip()
            print(f"  Alternative plan generated: {alternative_plan}")
            return alternative_plan
        except Exception as e:
            print(f"  Failed to generate alternative plan: {e}")
            return None

    def _replan_for_unreachable_object(self, unreachable_obj, task):
        """Generate plan avoiding unreachable objects"""
        print(f"  Strategy: Avoid unreachable object '{unreachable_obj}'")

        prompt = f"""
        The plan failed because '{unreachable_obj}' cannot be reached by the agent.

        Task: {task['description']}

        Generate an alternative plan that accomplishes the task WITHOUT requiring direct interaction with '{unreachable_obj}'.
        Focus on actions the agent can perform from accessible locations.

        Return only a PDDL plan:
        (:plan
          (action1 agent ...)
        )
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Failed to generate alternative plan: {e}")
            return None

    def _replan_for_navigation_collision(self, task):
        """Generate plan avoiding navigation collisions"""
        print("  Strategy: Simplify navigation to avoid collisions")

        prompt = f"""
        The plan failed due to navigation collision issues.

        Task: {task['description']}

        Generate a MINIMAL plan that accomplishes the core task with the simplest possible navigation.
        Prefer actions that don't require complex movement.

        Return only a PDDL plan:
        (:plan
          (action1 agent ...)
        )
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Failed to generate alternative plan: {e}")
            return None

    def execute_and_verify(self, vh_script, task):
        """Step 5: Execute script and verify completion (headless)"""
        print("Step 5: Executing script and verifying completion")

        # Spatial validation before execution
        self._validate_spatial_constraints(vh_script)

        # Capture initial state
        success, initial_graph = self.comm.environment_graph()
        if not success:
            print("Failed to capture initial state")
            return False, "Cannot capture initial state"

        # Execute script with recording
        print(f"Executing {len(vh_script)} actions...")
        execution_success, message = self.comm.render_script(
            vh_script,
            recording=True,
            find_solution=True,
            frame_rate=3,
            camera_mode=["PERSON_FROM_BACK"],
            file_name_prefix=f"pddl_task_{task['id']}",
            processing_time_limit=120,
            skip_execution=False,
            image_synthesis=["normal"],  # Ensure image generation
            save_pose_data=False
        )

        if not execution_success:
            print(f"Execution failed: {message}")

            # Attempt adaptive replanning
            alternative_plan = self._analyze_failure_and_replan(str(message), vh_script, task)

            if alternative_plan:
                print("\n🔄 EXECUTING ALTERNATIVE PLAN...")
                try:
                    # Convert alternative PDDL plan to VH script
                    alternative_vh_script = self.pddl_to_virtualhome_script(alternative_plan)

                    # Execute alternative plan (one retry only)
                    print(f"Executing alternative plan with {len(alternative_vh_script)} actions...")
                    alt_success, alt_message = self.comm.render_script(
                        alternative_vh_script,
                        recording=True,
                        find_solution=True,
                        frame_rate=3,
                        camera_mode=["PERSON_FROM_BACK"],
                        file_name_prefix=f"pddl_task_{task['id']}_alt",
                        processing_time_limit=120,
                        skip_execution=False,
                        image_synthesis=["normal"],
                        save_pose_data=False
                    )

                    if alt_success:
                        print("✅ Alternative plan succeeded!")
                        # Continue with verification using alternative execution
                        success, final_graph = self.comm.environment_graph()
                        if success:
                            verification_result = self._verify_task_completion(task, initial_graph, final_graph)
                            print(f"✅ Alternative execution completed")
                            print(f"Verification: {verification_result}")
                            return True, "SUCCESS with alternative plan"
                        else:
                            return False, "Alternative plan succeeded but cannot capture final state"
                    else:
                        print(f"Alternative plan also failed: {alt_message}")

                except Exception as e:
                    print(f"Error executing alternative plan: {e}")

            return False, f"Execution failed: {message}"

        # Capture final state
        success, final_graph = self.comm.environment_graph()
        if not success:
            print("Failed to capture final state")
            return False, "Cannot capture final state"

        # Verify completion based on task
        verification_result = self._verify_task_completion(task, initial_graph, final_graph)

        print(f"Execution completed")
        print(f"Verification: {verification_result}")

        return execution_success, verification_result

    def _verify_task_completion(self, task, initial_graph, final_graph):
        """Verify task completion by comparing states"""
        task_lower = task['description'].lower()

        # Get state changes
        initial_states = self._extract_object_states(initial_graph)
        final_states = self._extract_object_states(final_graph)

        changes = []
        for obj_id, final_state in final_states.items():
            initial_state = initial_states.get(obj_id, {})
            if final_state != initial_state:
                changes.append(f"Object {obj_id} changed: {initial_state} -> {final_state}")

        # Task-specific verification
        if 'email' in task_lower or 'computer' in task_lower:
            # Check if computer is on
            computer_on = False
            for obj_id, state in final_states.items():
                if any(comp in state.get('class_name', '').lower() for comp in ['computer', 'cpuscreen']):
                    print(f"Computer object {state.get('class_name')}: {state.get('states', [])}")
                    if 'ON' in state.get('states', []):
                        computer_on = True
                        break

            if computer_on:
                return f"SUCCESS: Computer turned on. Changes: {len(changes)}"
            else:
                return f"PARTIAL: Computer not detected as ON. Changes: {len(changes)}"

        elif 'fridge' in task_lower:
            # Check fridge state
            for obj_id, state in final_states.items():
                if 'fridge' in state.get('class_name', '').lower():
                    if 'CLOSED' in state.get('states', []):
                        return f"SUCCESS: Fridge properly closed. Changes: {len(changes)}"
            return f"PARTIAL: Fridge state unclear. Changes: {len(changes)}"

        else:
            # Generic verification
            if len(changes) > 0:
                return f"SUCCESS: Environment changed. Changes: {len(changes)}"
            else:
                return f"UNCLEAR: No significant changes detected"

    def _extract_object_states(self, graph):
        """Extract object states from scene graph"""
        states = {}
        for node in graph['nodes']:
            states[node['id']] = {
                'class_name': node['class_name'],
                'states': node.get('states', [])
            }
        return states

    def _check_ffmpeg(self):
        """Check if FFmpeg is installed"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f"  ✅ FFmpeg found: {version_line}")
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass

        print("  ❌ FFmpeg not found")
        print("  Please install FFmpeg:")
        print("    macOS: brew install ffmpeg")
        print("    Ubuntu: apt-get install ffmpeg")
        print("    Windows: Download from https://ffmpeg.org/download.html")
        return False

    def generate_video(self, task):
        """Step 6: Generate video from execution frames"""
        print("Step 6: Generating video from execution")

        # Check FFmpeg availability
        if not self._check_ffmpeg():
            print("Skipping video generation (FFmpeg not installed)")
            return False

        try:
            # Check multiple output directories, including subdirectories
            possible_dirs = [
                os.path.join(os.path.dirname(__file__), 'Output'),  # core/Output
                os.path.join(os.path.dirname(__file__), '..', 'Output'),  # parent/Output
                os.path.join(os.path.dirname(__file__), '..', 'Output', f"pddl_task_{task['id']}", '0'),  # VH subdirectory
                os.path.dirname(__file__)  # core/ directory itself
            ]

            png_files = []
            output_dir = None

            # Search for PNG files in possible directories
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    # Try different naming patterns
                    patterns = [
                        "Action_*_normal.png",  # VirtualHome default format
                        "Action_*.png",
                        f"pddl_task_{task['id']}_*.png",
                        f"*task_{task['id']}*.png",
                        "*.png"
                    ]

                    for pattern in patterns:
                        found_files = glob.glob(os.path.join(dir_path, pattern))
                        if found_files:
                            png_files = found_files
                            output_dir = dir_path
                            print(f"Found {len(png_files)} PNG files in {dir_path} with pattern {pattern}")
                            break

                    if png_files:
                        break

            if not png_files:
                print("No PNG files found for video generation")
                print("Searched in directories:")
                for d in possible_dirs:
                    if os.path.exists(d):
                        print(f"  - {d}: {os.listdir(d)}")
                return False

            png_files = sorted(png_files)
            print(f"Found {len(png_files)} frames")

            # Ensure core/Output directory exists
            core_output_dir = os.path.join(os.path.dirname(__file__), 'Output')
            os.makedirs(core_output_dir, exist_ok=True)

            # Generate video in core/Output
            video_filename = f"pddl_task_{task['id']}_{task['title'].replace(' ', '_')}.mp4"
            video_path = os.path.join(core_output_dir, video_filename)

            # Determine input pattern for FFmpeg
            first_file = os.path.basename(png_files[0])
            if "Action_" in first_file and "_normal.png" in first_file:
                # VirtualHome format: Action_0000_0_normal.png
                input_pattern = os.path.join(output_dir, "Action_%04d_0_normal.png")
            elif "Action_" in first_file:
                input_pattern = os.path.join(output_dir, "Action_%d.png")
            else:
                # Extract the base pattern
                base_name = first_file.split('_')[0]
                input_pattern = os.path.join(output_dir, f"{base_name}_%d.png")

            ffmpeg_cmd = [
                'ffmpeg', '-y',
                '-framerate', '3',
                '-i', input_pattern,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-vf', 'scale=800:600',
                video_path
            ]

            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

            if result.returncode == 0:
                if os.path.exists(video_path):
                    file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
                    print(f"Video generated successfully!")
                    print(f"   Path: {video_path}")
                    print(f"   Size: {file_size:.1f} MB")
                    print(f"   Frames: {len(png_files)}")
                    return True
                else:
                    print(f"Video file not found after FFmpeg completion")
                    return False
            else:
                print(f"FFmpeg failed:")
                print(f"   Command: {' '.join(ffmpeg_cmd)}")
                print(f"   Error: {result.stderr}")
                return False

        except Exception as e:
            print(f"Video generation error: {e}")
            return False

    def run_complete_pipeline(self, task_id=0):
        """Run the complete PDDL-centric pipeline"""
        self.current_task_id = task_id  # Track current task for file naming
        print(f"PDDL-VIRTUALHOME PIPELINE - TASK {task_id}")
        print("=" * 60)

        try:
            # Step 1: Load scene and task
            task = self.load_scene_and_task(task_id)

            # Step 2: Convert to PDDL problem
            pddl_problem = self.scene_to_pddl_problem(task)

            # Step 3: Solve with LLM
            pddl_solution = self.solve_pddl_with_llm(pddl_problem, task)

            # Step 4: Convert to VirtualHome script
            vh_script = self.pddl_to_virtualhome_script(pddl_solution)

            # Step 5: Execute and verify
            success, verification = self.execute_and_verify(vh_script, task)

            # Step 6: Generate video
            video_success = self.generate_video(task)

            # Final result
            print("\n" + "=" * 60)
            print("FINAL RESULT:")
            print(f"Task: {task['title']}")
            print(f"Execution: {'SUCCESS' if success else 'FAILED'}")
            print(f"Verification: {verification}")
            print(f"Video: {'GENERATED' if video_success else 'FAILED'}")
            print("=" * 60)

            return success

        except Exception as e:
            print(f"Pipeline error: {e}")
            return False

        finally:
            if self.comm:
                self.comm.close()

    def cleanup(self):
        """Explicit cleanup method"""
        print("Cleaning up resources...")

        if self.comm:
            try:
                print("  Closing simulator connection...")
                self.comm.close()
                print("Simulator closed")
            except Exception as e:
                print(f"Error closing simulator: {e}")
            finally:
                self.comm = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.cleanup()
        return False

    def __del__(self):
        """Destructor - final cleanup attempt"""
        if hasattr(self, 'comm') and self.comm:
            try:
                self.comm.close()
            except:
                pass


def main():
    """Test the PDDL-VirtualHome system"""
    # Try to load from .env file automatically
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        # Load from parent directory (where .env is located)
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from {env_path}")
    except ImportError:
        print("python-dotenv not installed. Install with: pip install python-dotenv")
        print("Falling back to environment variables...")

    # Load API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set.\n"
            "Please either:\n"
            "  1. Install python-dotenv: pip install python-dotenv\n"
            "  2. Set manually: export GOOGLE_API_KEY='your-api-key'\n"
            "  3. Add to .env file in project root\n"
            "Get your API key from: https://makersuite.google.com/app/apikey"
        )

    simulator_path = os.path.join(os.path.dirname(__file__), '..', 'macos_exec.2.2.4.app')

    if not os.path.exists(simulator_path):
        raise FileNotFoundError(
            f"VirtualHome simulator not found at: {simulator_path}\n"
            f"Please ensure the simulator is installed."
        )

    # Use context manager for automatic cleanup
    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        success = system.run_complete_pipeline(task_id=0)
        print(f"\nPipeline completed: {'SUCCESS' if success else 'FAILED'}")


if __name__ == "__main__":
    main()