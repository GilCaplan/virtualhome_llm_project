#!/usr/bin/env python3
"""PDDL problem generation module"""

import os

from ENV_VARS import PROJECT_PATH, GEMINI_MODEL_NAME, GEMINI_API_KEY


class PDDLGenerator:
    """Generates PDDL problems from VirtualHome scenes"""


    VIRTUALHOME_PDDL_DOMAIN_PATH = PROJECT_PATH + r"core\pddl_system\virtualhome_pddl_domain.pddl"
    with open(VIRTUALHOME_PDDL_DOMAIN_PATH, 'r') as f:
        virtualhome_domain_pddl = f.read()

    def __init__(self):
        self.current_scene_objects = {}

    def generate_goal_pddl_using_llm(self, task_description: str) -> str:
        """
        Generates PDDL goal conditions from a natural language task description using an LLM.
        Additionally, determines object-specific goal states using the LLM.
        """
        from google import genai
        print("Generating PDDL goal using LLM...")

        # Generate the main goal using the task description
        prompt = f"""
    Given the following PDDL domain definition:
    {self.virtualhome_domain_pddl}
    and the following task problem file with objects and initial conditions:
    {self.pddl_problem}
    Generate PDDL goal conditions for the following task description:
    Task Description: {task_description}
    Please provide only the PDDL goal conditions without any additional text.
    and only the content that goes inside the (:goal ...) section.
    Goal PDDL:
        """
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
        )
        main_goal_pddl = response.text.strip()

        # Extract objects from the PDDL problem
        objects_section = self.pddl_problem.split("(:objects")[1].split(")")[0]
        objects = [line.split("-")[0].strip() for line in objects_section.split("\n") if line.strip()]

        # Generate object-specific goals
        object_goals = []
        for obj in objects:
            obj_prompt = f"""
    Given the following PDDL domain definition:
    {self.virtualhome_domain_pddl}
    Determine if the object '{obj}' has a specific goal state it needs to be in by the end of the task.
    If it does, provide the goal condition in PDDL format. If not, write false in the response.
    Goal condition for '{obj}':
            """
            #     and the following task problem file with objects and initial conditions:
            #     {self.pddl_problem}
            obj_response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=obj_prompt,
            )
            obj_goal = obj_response.text.strip()
            if "false" not in obj_goal.lower():
                object_goals.append(obj_goal)
                print("obj_goal", obj, obj_goal)
            else:
                print("obj_goal", obj, "false")

        # Combine the main goal with object-specific goals
        combined_goal_pddl = f"""
    (and
    {main_goal_pddl}
    {'\n'.join(object_goals)}
    )
        """
        print(f"Generated Combined Goal PDDL: {combined_goal_pddl}")
        return combined_goal_pddl

    # Use LLM to decide which objects in the environment are related to the task and which can be removed
    def condense_scene_graph(self, task_description: str, objects_in_scene: set) -> dict:
        """
        Condenses the scene graph by identifying relevant objects for the given task using an LLM.
        :param task_description: Natural language description of the task.
        :param objects_in_scene: List of object names present in the scene.
        :return: A dictionary containing for each object whether it is relevant or not.
        """
        from google import genai
        from pydantic import BaseModel
        print("Condensing scene graph using LLM...")

        # use the "Structured output" API

        class ObjectRelevance(BaseModel):
            object_name: str
            relevant: bool

        prompt = f"""
            Given the following task description: "{task_description}" and the following list of objects in the scene: {objects_in_scene}
            Determine which objects are relevant to completing the task.
            An object is relevant also if it is only slightly related to the task or may be needed indirectly.
            For all the objects listed provide a decision whether they are relevant or not to the task.
            """
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": list[ObjectRelevance],
            },
        )
        relevant_objects_list: list[ObjectRelevance] = response.parsed

        relevant_objects_dict = {obj.object_name: obj.relevant for obj in relevant_objects_list}
        print(f"Relevant objects: {relevant_objects_dict}")
        return relevant_objects_dict


    def scene_graph_to_pddl_problem(self, task: str):
        """
        Converts a VirtualHome scene graph and task into a PDDL (Planning Domain Definition Language) problem.
        It categorizes objects in the scene, defines their types, initial states, and relationships, and generates a
        PDDL problem file with objects, initial conditions, and goal conditions. The function ensures the scene graph is
        valid, maps object properties to actions, and saves the generated PDDL problem to a task-specific directory for
        use in automated planning.
        """
        print("Step 2: Converting scene to PDDL problem")
        # scene_graph is a dict with 'nodes' and 'edges'
        # each nodes is a dict with 'id', 'class_name', 'category', 'properties', 'states'
        # set(value for sublist in [node['properties'] for node in graphs['init_graph']['nodes']] for value in sublist)
        # properties may be one of: {'CAN_OPEN', 'CLOTHES', 'CONTAINERS', 'COVER_OBJECT', 'CUTTABLE', 'DRINKABLE', 'EATABLE', 'GRABBABLE', 'HANGABLE', 'HAS_PAPER', 'HAS_PLUG', 'HAS_SWITCH', 'LIEABLE', 'LOOKABLE', 'MOVABLE', 'POURABLE', 'READABLE', 'RECIPIENT', 'SITTABLE', 'SURFACES'}
        # states may be one of: {'CLEAN', 'CLOSED', 'DIRTY', 'OFF', 'ON', 'OPEN', 'PLUGGED_IN', 'PLUGGED_OUT', 'SITTING'}
        # category may be one of: {'Appliances', 'Ceiling', 'Characters', 'Decor', 'Doors', 'Electronics', 'Floor', 'Floors', 'Furniture', 'Lamps', 'Props', 'Rooms', 'Walls', 'Windows', 'placable_objects'}
        scene_graph = task['initial_graph']

        if 'nodes' not in scene_graph or not isinstance(scene_graph['nodes'], list):
            raise ValueError("Invalid scene graph format: 'nodes' key missing or not a list")

        nodes = scene_graph['nodes']
        edges = scene_graph['edges']
        objects = []  # object declarations
        character_objects = []  # all the objects that are of type character
        objects_relevant_map = self.condense_scene_graph(task['title'],
                                                         set([node.get("class_name", f"obj_{node['id']}") for node in nodes]))
        objects_to_always_keep = ['character', 'floor']
        for obj_to_keep in objects_to_always_keep:
            objects_relevant_map[obj_to_keep] = True
        objects_to_ignore = set()
        init = []  # initial state predicates
        used_names = set()
        node_name_map = {}  # maps node id -> safe object name
        open_containers = set()
        rooms = set()
        def make_safe_name(name, id_):
            safe_name = f"{name.lower()}_{id_}"
            # while safe_name in used_names:
            #     safe_name += "_x"
            # used_names.add(safe_name)
            return safe_name
        def infer_type(node):
            """
            Infer object type based on properties and category
            """
            props = [p.upper() for p in node.get("properties", [])]
            category = node.get("category", "object")
            # based on properties and category
            # category may be one of: {'Appliances', 'Ceiling', 'Characters', 'Decor', 'Doors', 'Electronics', 'Floor',
            # 'Floors', 'Furniture', 'Lamps', 'Props', 'Rooms', 'Walls', 'Windows', 'placable_objects'}
            # properties may be one of: {'CAN_OPEN', 'CLOTHES', 'CONTAINERS', 'COVER_OBJECT', 'CUTTABLE', 'DRINKABLE',
            # 'EATABLE', 'GRABBABLE', 'HANGABLE', 'HAS_PAPER', 'HAS_PLUG', 'HAS_SWITCH', 'LIEABLE', 'LOOKABLE',
            # 'MOVABLE', 'POURABLE', 'READABLE', 'RECIPIENT', 'SITTABLE', 'SURFACES'}

            if category == "Rooms":
                return "room"
            elif category == "Characters":
                return "agent"
            elif "CAN_OPEN" in props and "CONTAINERS" in props:
                return "container-objectt"
            elif "HAS_SWITCH" in props:
                return "switchable-objectt"
            elif "SURFACES" in props:
                return "surface-objectt"
            elif "GRABBABLE" in props:
                return "grabbable-objectt"
            elif "SITTABLE" in props:
                return "sittable-objectt"
            else:
                print(node)
                return "other"


        obj_types = {}  # map object name to type

        # is object needed for the pddl
        needed_objects = set()
        for node in nodes:
            obj_type = infer_type(node)
            obj_name = make_safe_name(node.get("class_name", "obj"), node["id"])
            if obj_type == "other":
                continue

            if obj_type == "room":
                needed_objects.add(obj_name)
                continue

            # ✅ PDDL Problem created with 54 objects, 333 init conditions
            # ✅ PDDL Problem created with 168 objects, 1900 init conditions
            if objects_relevant_map.get(node.get("class_name", f"obj_{node['id']}"), False):
                needed_objects.add(obj_name)
                continue

        # for all the nodes that were not added, if they have an edge to a needed object, add them as well
        additional_needed_objects = set()
        for node in nodes:
            obj_type = infer_type(node)
            if obj_type == "other":
                continue
            obj_name = make_safe_name(node.get("class_name", "obj"), node["id"])
            if obj_name in needed_objects:
                continue
            for edge in edges:
                relation_type = edge["relation_type"].upper()
                if relation_type in ["CLOSE", "FACING", "BETWEEN"]:
                    continue

                if edge["from_id"] == node["id"]:
                    to_node = next(n for n in nodes if n["id"] == edge["to_id"])
                    to_obj_name = make_safe_name(to_node.get("class_name", "obj"), to_node["id"])
                    to_obj_type = infer_type(to_node)
                    # if the relation is object INSIDE room skip it
                    if relation_type == "INSIDE" and to_obj_type == "room":
                        continue
                    # if the relation type is ON and the object ON floor skip it
                    if relation_type == "ON" and "floor" in to_obj_name:
                        continue
                    if to_obj_name in needed_objects:
                        additional_needed_objects.add(obj_name)
                        print(f"Also adding {obj_name} because it connects to needed object {to_obj_name} ({edge})")
                        break
                elif edge["to_id"] == node["id"]:
                    from_node = next(n for n in nodes if n["id"] == edge["from_id"])
                    from_obj_name = make_safe_name(from_node.get("class_name", "obj"), from_node["id"])
                    if from_obj_name in needed_objects:
                        additional_needed_objects.add(obj_name)
                        print(f"Also adding {obj_name} because it connects to needed object {from_obj_name} ({edge})")
                        break

        needed_objects.update(additional_needed_objects)

        for node in nodes:
            obj_type = infer_type(node)
            obj_name = make_safe_name(node.get("class_name", "obj"), node["id"])
            if obj_name not in needed_objects:
                continue

            objects.append(f"{obj_name} - {obj_type}")
            node_name_map[node["id"]] = obj_name
            if obj_type == "character":
                character_objects.append(obj_name)
            elif obj_type == "room":
                rooms.add(obj_name)
            obj_types[obj_name] = obj_type

            # all surfaces and containers are reachable
            if obj_type in ["surface-objectt", "container-objectt"]:
                init.append(f"(always-reachable {obj_name})")

            # possible predicates according to domain: holding, grabbable, drinkable, switchable, on, off, open, closed, sittable, reachable, in-room, in-container, on-surface
            for state in node.get("states", []):
                state_upper = state.upper()
                if state_upper == "OPEN":
                    if obj_type == "container-objectt":
                        init.append(f"(is-open {obj_name})")
                        init.append(f"(not (is-closed {obj_name}))")
                        open_containers.add(obj_name)
                elif state_upper == "CLOSED":
                    if obj_type == "container-objectt":
                        init.append(f"(not(is-open {obj_name}))")
                        init.append(f"(is-closed {obj_name})")
                elif state_upper == "ON":
                    if obj_type == "switchable-objectt":
                        init.append(f"(on {obj_name})")
                elif state_upper == "OFF":
                    if obj_type == "switchable-objectt":
                        init.append(f"(not(on {obj_name}))")

            # properties may be one of: {'CAN_OPEN', 'CLOTHES', 'CONTAINERS', 'COVER_OBJECT', 'CUTTABLE', 'DRINKABLE',
            # 'EATABLE', 'GRABBABLE', 'HANGABLE', 'HAS_PAPER', 'HAS_PLUG', 'HAS_SWITCH', 'LIEABLE', 'LOOKABLE',
            # 'MOVABLE', 'POURABLE', 'READABLE', 'RECIPIENT', 'SITTABLE', 'SURFACES'}
            # for prop in node.get("properties", []):
            #     prop_upper = prop.upper()
                # if prop_upper == "GRABBABLE":
                #     init.append(f"(grabbable {obj_name})")
                # elif prop_upper == "DRINKABLE":
                #     init.append(f"(drinkable {obj_name})")
                # elif prop_upper == "HAS_SWITCH":
                #     init.append(f"(switchable {obj_name})")



        for edge in edges:
            # edge has 'from_id', 'to_id', 'relation_type'
            # relation_type may be one of: {'BETWEEN', 'CLOSE', 'FACING', 'INSIDE', 'ON'}
            from_node = next(n for n in nodes if n["id"] == edge["from_id"])
            to_node = next(n for n in nodes if n["id"] == edge["to_id"])
            if from_node["id"] not in node_name_map:
                print(edge)
                continue
            from_name = node_name_map[from_node["id"]]
            if to_node["id"] not in node_name_map:
                print(edge)
                continue
            to_name = node_name_map[to_node["id"]]
            rel_type = edge["relation_type"].upper()
            if rel_type == "CLOSE":
                object_types = ["objectt", "sittable-objectt", "switchable-objectt", "container-objectt",
                                "surface-objectt", "grabbable-objectt", "static-objectt"]
                if from_name in character_objects:
                    init.append(f"(close {from_name} {to_name})")
                elif obj_types.get(from_name) in object_types:
                    init.append(f"(close-objects {from_name} {to_name})")
            elif rel_type == "FACING":
                if from_name in character_objects:
                    init.append(f"(facing {from_name} {to_name})")
            elif rel_type == "INSIDE":
                if obj_types.get(to_name) == "room":
                    if obj_types.get(from_name) == "agent":
                        init.append(f"(at {from_name} {to_name})")
                    else:
                        init.append(f"(in-room {from_name} {to_name})")
                elif obj_types.get(to_name) == "container-objectt":
                    init.append(f"(in-container {from_name} {to_name})")
                    # if the container is open the item inside is reachable
                    if to_name in open_containers:
                        # init.append(f"(reachable-inside-container {from_name} {to_name})")
                        pass
            elif rel_type == "ON":
                if obj_types.get(from_name) == "grabbable-objectt" and obj_types.get(to_name) == "surface-objectt":
                    init.append(f"(on-surface {from_name} {to_name})")
                    # if the object is on a surface it means it is reachable
                    init.append(f"(reachable-on-surface {from_name} {to_name})")
            elif rel_type == "BETWEEN":
                pass  # ignore for now

        # if the object is not on any surface or inside any container, and is in a room, we will say it is on the floor
        for node in nodes:
            from_name = node_name_map.get(node["id"])
            if from_name is None:
                continue
            from_type = infer_type(node)
            if from_type in ["grabbable-objectt", "sittable-objectt", "switchable-objectt", "container-objectt"]:
                # check if the object is already placed somewhere
                placed = False
                for edge in edges:
                    if edge["from_id"] == node["id"]:
                        rel_type = edge["relation_type"].upper()
                        to_id = edge["to_id"]
                        to_name = node_name_map.get(to_id)
                        to_type = obj_types.get(to_name)
                        if rel_type in ["ON", "INSIDE"] and to_type != "room":
                            placed = True
                            break
                if not placed:
                    # find the room it is in
                    for edge in edges:
                        if edge["from_id"] == node["id"]:
                            to_node = next(n for n in nodes if n["id"] == edge["to_id"])
                            to_name = node_name_map.get(to_node["id"], None)
                            if to_name is None:
                                continue
                            to_type = infer_type(to_node)
                            if edge["relation_type"].upper() == "INSIDE" and to_type == "room":
                                init.append(f"(reachable-inside-room {from_name} {to_name})")
                                break

        print(f"Creating PDDL Problem with {len(objects)} objects and {len(init)} initial conditions")
        # write to PDDL problem file
        pddl_problem = f"""
    (define (problem vh_task_{task['task_id']}_{task['title'].replace(" ", "_")})
        (:domain virtualhome)
        (:objects
            obj_agent_0 - agent
            {'\n'.join(objects)}
        )
        (:init
            (has-free-hand obj_agent_0)  ;; agent starts with free hand
            (not (sitting obj_agent_0))  ;; agents is not sitting at start
            (standing obj_agent_0)  ;; agent is standing at start
            (not(ready-to-move-to-next-obj obj_agent_0))  ;; agent is ready to move at start
            (not-ready-to-move-to-next-obj obj_agent_0)  ;; agent is not ready to move at start
            {'\n'.join(init)}
        )
        (:goal
            ;; To be filled in using LLM based on task description
        )
        )
        """
        self.pddl_problem = pddl_problem

        # Generate goal using LLM
        goal_pddl = self.generate_goal_pddl_using_llm(task['title'])
        pddl_problem = pddl_problem.replace(
            ";; To be filled in using LLM based on task description",
            goal_pddl
        )
        self.pddl_problem = pddl_problem

        print(f"✅ PDDL Problem created with {len(objects)} objects, {len(init)} init conditions")

        # Save the PDDL problem file
        problem_filename = f"vh_task_{task['task_id']}_{task['title']}.pddl"
        problem_file_path = PROJECT_PATH + r"core\pddl_system\tasks"
        os.makedirs(problem_file_path, exist_ok=True)
        full_problem_path = os.path.join(problem_file_path, problem_filename)
        with open(full_problem_path, 'w') as f:
            f.write(pddl_problem)
        print(f"✅ PDDL Problem saved to: {full_problem_path}")
        return pddl_problem

