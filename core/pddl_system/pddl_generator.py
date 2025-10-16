#!/usr/bin/env python3
"""PDDL problem generation module"""

import os


class PDDLGenerator:
    """Generates PDDL problems from VirtualHome scenes"""

    # PDDL Domain for VirtualHome
    VIRTUALHOME_DOMAIN = """
    (define (domain virtualhome)
      (:requirements :strips :typing)

      (:types
        agent
        room
        furniture
        appliance
        container
        object
      )

      (:predicates
        ;; --- Agent state ---
        (at ?agent - agent ?loc - room)                 ; agent is currently in a room
        (sitting ?agent - agent)                        ; agent is sitting
        (holding ?agent - agent ?obj - object)          ; agent is holding an object
        (facing ?agent - agent ?obj - object)           ; agent is facing an object
        (close ?agent - agent ?obj - object)            ; agent is near enough to interact
        (has-free-hand ?agent - agent)                  ; agent has a free hand for grabbing

        ;; --- Object states ---
        (grabbable ?obj - object)                       ; object can be grabbed
        (drinkable ?obj - object)                       ; object can be drunk from
        (switchable ?obj - appliance)                   ; object can be turned on/off
        (on ?obj - appliance)                           ; appliance is on
        (off ?obj - appliance)                          ; appliance is off
        (open ?obj - container)                         ; container is open
        (closed ?obj - container)                       ; container is closed
        (sittable ?obj - furniture)                     ; object can be sat on
        (reachable ?obj - object)                       ; object is not inside closed container

        ;; --- Spatial relations ---
        (in-room ?obj - object ?room - room)            ; object is located in a room
        (in-container ?obj - object ?container - container) ; object is inside container
        (on-surface ?obj - object ?surf - object)       ; object is placed on top of another
      )

      ;; ---------------------------------------------------------------------------
      ;; MOVEMENT ACTIONS
      ;; ---------------------------------------------------------------------------

      (:action walk
        :parameters (?agent - agent ?target - object)
        :precondition (and (not (sitting ?agent)) (reachable ?target))
        :effect (and (close ?agent ?target))
      )

      (:action run
        :parameters (?agent - agent ?target - object)
        :precondition (and (not (sitting ?agent)) (reachable ?target))
        :effect (and (close ?agent ?target))
      )

      (:action walktowards
        :parameters (?agent - agent ?target - object)
        :precondition (and (not (sitting ?agent)) (reachable ?target))
        :effect (and (close ?agent ?target))
      )

      (:action walkforward
        :parameters (?agent - agent)
        :precondition (not (sitting ?agent))
        :effect (and) ; moves 1 meter forward
      )

      (:action turnleft
        :parameters (?agent - agent)
        :precondition (not (sitting ?agent))
        :effect (and) ; rotates 30° left
      )

      (:action turnright
        :parameters (?agent - agent)
        :precondition (not (sitting ?agent))
        :effect (and) ; rotates 30° right
      )

      ;; ---------------------------------------------------------------------------
      ;; SITTING / STANDING
      ;; ---------------------------------------------------------------------------

      (:action sit
        :parameters (?agent - agent ?seat - furniture)
        :precondition (and
          (not (sitting ?agent))
          (close ?agent ?seat)
          (sittable ?seat)
        )
        :effect (sitting ?agent)
      )

      (:action standup
        :parameters (?agent - agent)
        :precondition (sitting ?agent)
        :effect (not (sitting ?agent))
      )

      ;; ---------------------------------------------------------------------------
      ;; OBJECT MANIPULATION
      ;; ---------------------------------------------------------------------------

      (:action grab
        :parameters (?agent - agent ?obj - object)
        :precondition (and
          (grabbable ?obj)
          (reachable ?obj)
          (close ?agent ?obj)
          (has-free-hand ?agent)
        )
        :effect (and
          (holding ?agent ?obj)
          (not (has-free-hand ?agent))
        )
      )

      (:action put
        :parameters (?agent - agent ?obj - object ?surf - object)
        :precondition (and (holding ?agent ?obj) (close ?agent ?surf))
        :effect (and
          (not (holding ?agent ?obj))
          (on-surface ?obj ?surf)
          (has-free-hand ?agent)
        )
      )

      (:action putin
        :parameters (?agent - agent ?obj - object ?cont - container)
        :precondition (and
          (holding ?agent ?obj)
          (open ?cont)
          (close ?agent ?cont)
        )
        :effect (and
          (not (holding ?agent ?obj))
          (in-container ?obj ?cont)
          (has-free-hand ?agent)
        )
      )

      ;; ---------------------------------------------------------------------------
      ;; CONTAINER INTERACTIONS
      ;; ---------------------------------------------------------------------------

      (:action open
        :parameters (?agent - agent ?cont - container)
        :precondition (and
          (closed ?cont)
          (reachable ?cont)
          (close ?agent ?cont)
          (has-free-hand ?agent)
        )
        :effect (and (open ?cont) (not (closed ?cont)))
      )

      (:action close
        :parameters (?agent - agent ?cont - container)
        :precondition (and
          (open ?cont)
          (reachable ?cont)
          (close ?agent ?cont)
          (has-free-hand ?agent)
        )
        :effect (and (closed ?cont) (not (open ?cont)))
      )

      ;; ---------------------------------------------------------------------------
      ;; APPLIANCE INTERACTIONS
      ;; ---------------------------------------------------------------------------

      (:action switchon
        :parameters (?agent - agent ?app - appliance)
        :precondition (and
          (switchable ?app)
          (off ?app)
          (close ?agent ?app)
        )
        :effect (and (on ?app) (not (off ?app)))
      )

      (:action switchoff
        :parameters (?agent - agent ?app - appliance)
        :precondition (and
          (switchable ?app)
          (on ?app)
          (close ?agent ?app)
        )
        :effect (and (off ?app) (not (on ?app)))
      )

      ;; ---------------------------------------------------------------------------
      ;; OTHER INTERACTIONS
      ;; ---------------------------------------------------------------------------

      (:action drink
        :parameters (?agent - agent ?obj - object)
        :precondition (and (close ?agent ?obj) (drinkable ?obj))
        :effect (and) ; consume from object
      )

      (:action touch
        :parameters (?agent - agent ?obj - object)
        :precondition (and (close ?agent ?obj) (reachable ?obj))
        :effect (and) ; touch interaction
      )

      (:action lookat
        :parameters (?agent - agent ?obj - object)
        :precondition (and (facing ?agent ?obj) (reachable ?obj))
        :effect (and) ; agent now focused on object
      )
    )
    """

    def __init__(self):
        self.current_scene_objects = {}

    def scene_to_pddl_problem(self, task, scene_graph):
        """Convert scene and task to PDDL problem"""
        print("Step 2: Converting scene to PDDL problem")

        # Create concise PDDL problem
        objects_section = []
        init_section = []

        # Categorize objects
        rooms = []
        furniture = []
        appliances = []
        interactive_objects = []

        # Track unique object names
        object_names_seen = set()
        base_name_to_ids = {}
        non_interactable_objects = []

        # Validate scene_graph
        if scene_graph is None:
            print("❌ Error: scene_graph is None - cannot generate PDDL problem")
            return None

        if 'nodes' not in scene_graph or scene_graph['nodes'] is None:
            print("❌ Error: scene_graph has no 'nodes' - cannot generate PDDL problem")
            return None

        # Define interactable properties
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

            # Categorize based on scene graph properties
            if any(room in base_name for room in ['kitchen', 'bedroom', 'bathroom', 'living', 'office', 'hallway']):
                rooms.append(name)
                objects_section.append(f"{name} - room")

            elif 'SITTABLE' in properties:
                furniture.append(name)
                objects_section.append(f"{name} - furniture")
                init_section.append(f"(can-sit agent {name})")

            elif category == 'Furniture' and has_interactable_property:
                furniture.append(name)
                objects_section.append(f"{name} - furniture")
                if 'SITTABLE' in properties:
                    init_section.append(f"(can-sit agent {name})")

            elif 'HAS_SWITCH' in properties:
                # Filter out objects that are grabbable but not true appliances
                if 'GRABBABLE' in properties and 'remote' in name:
                    # Remote controls are grabbable items, not switchable appliances
                    interactive_objects.append(name)
                    objects_section.append(f"{name} - interactive-object")
                    init_section.append(f"(grabbable {name})")
                else:
                    appliances.append(name)
                    objects_section.append(f"{name} - appliance")
                    if 'ON' in states:
                        init_section.append(f"(on {name})")
                    else:
                        init_section.append(f"(off {name})")

            elif category == 'Electronics' and has_interactable_property:
                appliances.append(name)
                objects_section.append(f"{name} - appliance")
                if 'ON' in states:
                    init_section.append(f"(on {name})")
                elif 'OFF' in states:
                    init_section.append(f"(off {name})")

            elif category == 'Lamps':
                if 'HAS_SWITCH' in properties:
                    appliances.append(name)
                    objects_section.append(f"{name} - appliance")
                    if 'ON' in states:
                        init_section.append(f"(on {name})")
                    else:
                        init_section.append(f"(off {name})")
                else:
                    non_interactable_objects.append(name)

            elif 'fridge' in name:
                appliances.append(name)
                objects_section.append(f"{name} - container")
                init_section.append(f"(closed {name})")
                init_section.append(f"(accessible {name})")
                init_section.append(f"(can-interact agent {name})")

            elif 'CAN_OPEN' in properties or category in ['Doors']:
                interactive_objects.append(name)
                objects_section.append(f"{name} - interactive-object")

            elif 'GRABBABLE' in properties:
                interactive_objects.append(name)
                objects_section.append(f"{name} - interactive-object")
                init_section.append(f"(grabbable {name})")

            elif not has_interactable_property:
                non_interactable_objects.append(name)

            else:
                interactive_objects.append(name)
                objects_section.append(f"{name} - interactive-object")

        # Add agent
        objects_section.insert(0, "agent - agent")
        init_section.append("(at agent kitchen)")

        # Add room containment
        for room in rooms:
            for obj in furniture + appliances + interactive_objects:
                if 'computer' in obj or 'keyboard' in obj or 'desk' in obj:
                    if 'bedroom' in room:
                        init_section.append(f"(in-room {obj} {room})")
                elif 'fridge' in obj or 'stove' in obj:
                    if 'kitchen' in room:
                        init_section.append(f"(in-room {obj} {room})")

        # Generic goal: Let LLM infer from task description
        # No hardcoded task-specific goals - purely PDDL reasoning
        goal_conditions = [
            "; Goal will be inferred by LLM from task description",
            "; LLM has full task context and domain knowledge"
        ]

        # Build object capability map
        object_capabilities = self.build_object_capabilities(scene_graph)

        # Store categorized objects
        self.current_scene_objects = {
            'rooms': rooms,
            'furniture': furniture,
            'appliances': appliances,
            'interactive_objects': interactive_objects,
            'non_interactable': non_interactable_objects,
            'capabilities': object_capabilities
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

        # Save PDDL problem to task-specific directory
        task_dir = f"Output/task_{task['task_id']}"
        os.makedirs(task_dir, exist_ok=True)
        pddl_filename = os.path.join(task_dir, "pddl_problem.txt")
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

    def build_object_capabilities(self, scene_graph):
        """Build mapping from objects to valid actions based on properties"""
        # Property-to-action mapping from VirtualHome documentation
        PROPERTY_ACTION_MAP = {
            'GRABBABLE': ['FIND', 'GRAB'],
            'CAN_OPEN': ['FIND', 'OPEN', 'CLOSE'],
            'HAS_SWITCH': ['FIND', 'SWITCHON', 'SWITCHOFF', 'TYPE'],
            'SITTABLE': ['FIND', 'SIT'],
            'LOOKABLE': ['FIND', 'LOOKAT'],
            'RECIPIENT': ['FIND', 'DRINK', 'POUR_INTO'],
            'SURFACES': ['FIND', 'PUTBACK_ON'],
            'CONTAINERS': ['FIND', 'PUTIN'],
            'READABLE': ['FIND', 'READ'],
            'DRINKABLE': ['FIND', 'DRINK'],
            'EATABLE': ['FIND', 'EAT'],
            'POURABLE': ['FIND', 'POUR'],
            'MOVABLE': ['FIND', 'MOVE', 'PUSH', 'PULL'],
            'HAS_PLUG': ['FIND', 'PLUGIN', 'PLUGOUT'],
            'CLOTHES': ['FIND', 'PUTON', 'PUTOFF'],
            'LIEABLE': ['FIND', 'LIE'],
            'CUTTABLE': ['FIND', 'CUT']
        }

        capabilities = {}

        for node in scene_graph['nodes']:
            obj_name = node['class_name'].lower().replace(' ', '_')
            properties = node.get('properties', [])
            states = node.get('states', [])

            valid_actions = set()
            relevant_properties = []
            relevant_states = []

            for prop in properties:
                if prop in PROPERTY_ACTION_MAP:
                    relevant_properties.append(prop)
                    valid_actions.update(PROPERTY_ACTION_MAP[prop])

            for state in states:
                if state in ['ON', 'OFF', 'OPEN', 'CLOSED', 'PLUGGED_IN', 'PLUGGED_OUT', 'CLEAN', 'DIRTY']:
                    relevant_states.append(state)

            if valid_actions:
                capabilities[obj_name] = {
                    'actions': sorted(list(valid_actions)),
                    'properties': relevant_properties,
                    'states': relevant_states
                }

        return capabilities
