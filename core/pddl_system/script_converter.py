#!/usr/bin/env python3
"""
Script Converter Module

This module converts PDDL action plans to VirtualHome executable scripts.
It handles object name resolution, fuzzy matching, and action translation.
"""

import os
import re


class ScriptConverter:
    """
    Converts PDDL plans to VirtualHome scripts.

    Handles:
    - PDDL action parsing
    - Object ID mapping and resolution
    - Fuzzy object name matching
    - VirtualHome action formatting
    """

    def __init__(self, comm):
        """
        Initialize the script converter.

        Args:
            comm: VirtualHome simulator communication instance
        """
        self.comm = comm
        self.current_task_id = None

    def pddl_to_virtualhome_script(self, pddl_solution):
        """
        Convert PDDL solution to VirtualHome script.

        Args:
            pddl_solution: PDDL solution string with action plan

        Returns:
            list: VirtualHome script commands
        """
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

        # Save VirtualHome script to task-specific directory
        task_id = self.current_task_id if self.current_task_id is not None else 'unknown'
        task_dir = f"Output/task_{task_id}"
        os.makedirs(task_dir, exist_ok=True)
        script_filename = os.path.join(task_dir, "virtualhome_script.txt")
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
        """
        Get mapping from object names to VirtualHome IDs.

        Returns:
            dict: Mapping of object names to IDs and original names
        """
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
        """
        Fuzzy match object name with multiple strategies including spelling variations.

        Args:
            target_name: Target object name to match
            object_map: Dictionary of available objects

        Returns:
            tuple: (object_id, original_name) or (None, None) if not found
        """
        target_lower = target_name.lower().replace('-', '_').replace(' ', '_')

        # Strategy 0: Strip ID suffix if present (bedroom_74 -> bedroom)
        base_target = re.sub(r'_\d+$', '', target_lower)  # Remove _### at end

        # Strategy 1: Try base name without ID
        if base_target in object_map and base_target != target_lower:
            print(f"  Matched '{target_name}' to base '{base_target}'")
            return object_map[base_target], object_map.get(f"{base_target}_original", base_target)

        # Strategy 2: Exact match
        if target_lower in object_map:
            return object_map[target_lower], object_map.get(f"{target_lower}_original", target_name)

        # Strategy 3: Try variations (spacing, punctuation)
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

        # Strategy 4: Comprehensive semantic aliases and spelling variations
        # This handles common synonyms AND spelling variations (e.g., coffeemaker vs coffe_maker)
        aliases = {
            # Electronics and appliances
            'tv': ['television', 'tv_stand', 'tvstand'],
            'computer': ['pc', 'desktop', 'laptop', 'cpuscreen'],
            'fridge': ['refrigerator', 'icebox'],
            'remote': ['remote_control', 'tv_remote', 'controller', 'remotecontrol'],
            'phone': ['cellphone', 'cell_phone', 'telephone', 'smartphone'],
            'coffeemaker': ['coffee_maker', 'coffe_maker', 'coffemachine', 'coffee_machine'],

            # Furniture
            'couch': ['sofa'],
            'desk': ['table', 'worktable', 'work_table'],
            'bookshelf': ['bookcase', 'book_shelf'],

            # Containers and receptacles
            'cup': ['mug', 'glass', 'drinkglass'],
            'glass': ['cup', 'drinkglass', 'drinking_glass'],
            'bowl': ['dish'],

            # Reading materials
            'book': ['novel', 'textbook', 'magazine'],

            # Lights
            'lamp': ['light', 'ceilinglamp', 'ceiling_lamp', 'floorlamp', 'floor_lamp'],
            'light': ['lamp', 'ceilinglamp', 'ceiling_lamp'],

            # Bathroom items
            'sink': ['washbasin', 'basin'],
            'toothbrush': ['tooth_brush'],

            # Kitchen items
            'stove': ['cooker', 'oven'],
            'microwave': ['micro_wave'],

            # Wearables
            'glasses': ['eyeglasses', 'spectacles'],
        }

        # Check if target or any of its aliases match
        for alias_base, synonyms in aliases.items():
            # If target matches the base or any synonym
            if base_target == alias_base or base_target in synonyms:
                # Try all variations of the base and synonyms
                for synonym in [alias_base] + synonyms:
                    if synonym in object_map:
                        print(f"  Semantic matched '{target_name}' to '{synonym}'")
                        return object_map[synonym], object_map.get(f"{synonym}_original", synonym)

            # Also check reverse: if any key in object_map matches the alias group
            for key in object_map.keys():
                if '_original' not in key:
                    # Check if the key matches the base or any synonym
                    if key == alias_base or key in synonyms:
                        if base_target == alias_base or base_target in synonyms:
                            print(f"  Semantic matched '{target_name}' to '{key}' via aliases")
                            return object_map[key], object_map.get(f"{key}_original", key)

        # Strategy 5: Partial substring match (relaxed)
        for key in object_map.keys():
            if '_original' not in key:
                # Match if target is substring of key or vice versa (minimum 4 chars)
                if len(base_target) >= 4 and len(key) >= 4:
                    if base_target in key or key in base_target:
                        print(f"  Fuzzy matched '{target_name}' to '{key}'")
                        return object_map[key], object_map.get(f"{key}_original", key)

        # Strategy 6: Levenshtein distance for spelling errors
        # Only calculate for reasonable length matches to avoid performance issues
        if len(base_target) >= 4:
            best_match = None
            best_distance = float('inf')

            for key in object_map.keys():
                if '_original' not in key and len(key) >= 4:
                    # Calculate simple edit distance (Levenshtein)
                    distance = self._levenshtein_distance(base_target, key)
                    # Accept if distance is <= 2 (allows for 1-2 character typos)
                    if distance <= 2 and distance < best_distance:
                        best_distance = distance
                        best_match = key

            if best_match:
                print(f"  Spelling matched '{target_name}' to '{best_match}' (distance: {best_distance})")
                return object_map[best_match], object_map.get(f"{best_match}_original", best_match)

        # Failure
        print(f"  ⚠️ Object '{target_name}' not found in scene")
        available = [k for k in object_map.keys() if '_original' not in k][:20]
        print(f"  Available objects: {available}")
        return None, None

    def _levenshtein_distance(self, s1, s2):
        """
        Calculate Levenshtein distance between two strings for spelling correction.

        Args:
            s1: First string
            s2: Second string

        Returns:
            int: Edit distance between strings
        """
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # Cost of insertions, deletions, or substitutions
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _convert_pddl_action_to_vh(self, action_name, params, object_map):
        """
        Convert single PDDL action to VirtualHome action.

        Args:
            action_name: PDDL action name
            params: List of parameters
            object_map: Object ID mapping

        Returns:
            str: VirtualHome action string or None if conversion fails
        """
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
