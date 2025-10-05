#!/usr/bin/env python3
"""
Object Manager Module

This module handles detection and spawning of missing objects in the scene.
It ensures that objects required by the plan are present in the VirtualHome environment.
"""

import re


class ObjectManager:
    """
    Manages scene objects for VirtualHome tasks.

    Handles:
    - Detection of missing objects in scripts
    - Spawning missing objects into the scene
    - Object placement and initialization
    """

    def __init__(self, comm):
        """
        Initialize the object manager.

        Args:
            comm: VirtualHome simulator communication instance
        """
        self.comm = comm

    def _detect_missing_objects(self, vh_script, scene_graph):
        """
        Detect objects mentioned in script that don't exist in scene.

        Only considers objects "missing" if they have ID = 1 (fallback ID),
        indicating they weren't found during script conversion.

        Args:
            vh_script: List of VirtualHome script commands
            scene_graph: Scene graph dictionary

        Returns:
            list: Names of missing objects
        """
        # Extract object names AND their IDs from VirtualHome script
        # Format: <char0> [ACTION] <object> (id)
        script_objects_with_ids = {}
        for line in vh_script:
            # Match patterns like [FIND] <object> (id) or [GRAB] <object> (id)
            # Capture object name and ID separately
            obj_matches = re.findall(r'<(\w+)> \((\d+)\)', line)
            for obj_name, obj_id in obj_matches:
                if obj_name not in ['char0', 'character']:
                    script_objects_with_ids[obj_name] = int(obj_id)

        # Only consider objects with ID = 1 as "missing" (fallback ID from script_converter)
        missing = []
        for obj_name, obj_id in script_objects_with_ids.items():
            if obj_id == 1:  # Fallback ID indicates object wasn't found
                missing.append(obj_name)

        return missing

    def _spawn_missing_objects(self, missing_objects, scene_graph, task):
        """
        Spawn missing objects into the scene.

        Args:
            missing_objects: List of object names to spawn
            scene_graph: Current scene graph
            task: Task dictionary

        Returns:
            dict: Updated scene graph with spawned objects
        """
        if not missing_objects:
            return scene_graph

        print(f"\n🎨 SPAWNING MISSING OBJECTS: {', '.join(missing_objects)}")

        # Common missing objects and their VirtualHome counterparts
        spawn_mappings = {
            # Food & Kitchen Items
            'book': {'class_name': 'book', 'category': 'Books', 'properties': ['GRABBABLE', 'READABLE']},
            'groceries': {'class_name': 'food_apple', 'category': 'Food', 'properties': ['GRABBABLE', 'EATABLE']},
            'cereal': {'class_name': 'cereal', 'category': 'Food', 'properties': ['GRABBABLE', 'EATABLE']},
            'plate': {'class_name': 'plate', 'category': 'Plates', 'properties': ['GRABBABLE', 'SURFACES']},
            'glass': {'class_name': 'glass', 'category': 'Glasses', 'properties': ['GRABBABLE', 'RECIPIENT', 'DRINKABLE']},
            'cup': {'class_name': 'mug', 'category': 'Mugs', 'properties': ['GRABBABLE', 'RECIPIENT']},
            'water': {'class_name': 'waterglass', 'category': 'Glasses', 'properties': ['GRABBABLE', 'DRINKABLE']},

            # Electronics
            'phone': {'class_name': 'cellphone', 'category': 'Electronics', 'properties': ['GRABBABLE', 'HAS_SWITCH']},
            'remote': {'class_name': 'remotecontrol', 'category': 'Electronics', 'properties': ['GRABBABLE']},
            'remotecontrol': {'class_name': 'remotecontrol', 'category': 'Electronics', 'properties': ['GRABBABLE']},

            # Note: Large appliances (fridge, tv, sofa) and rooms (kitchen, bedroom, livingroom)
            # should NOT be spawned as they are typically part of the base scene.
            # If they're missing, it indicates a scene configuration issue, not a spawning need.
        }

        # Find a suitable location to spawn objects (kitchen table or counter)
        spawn_location = None
        for node in scene_graph['nodes']:
            if 'table' in node['class_name'].lower() or 'counter' in node['class_name'].lower():
                if 'SURFACES' in node.get('properties', []):
                    spawn_location = node
                    break

        if not spawn_location:
            # Default to kitchen if no table found
            for node in scene_graph['nodes']:
                if 'kitchen' in node['class_name'].lower():
                    spawn_location = node
                    break

        # Get next available ID
        max_id = max(node['id'] for node in scene_graph['nodes'])
        next_id = max_id + 1

        # Add missing objects to scene graph
        new_nodes = []
        for obj in missing_objects:
            obj_lower = obj.lower()
            if obj_lower in spawn_mappings:
                spawn_info = spawn_mappings[obj_lower]
                new_node = {
                    'id': next_id,
                    'class_name': spawn_info['class_name'],
                    'category': spawn_info['category'],
                    'properties': spawn_info['properties'],
                    'states': [],
                    'bounding_box': spawn_location.get('bounding_box', {}) if spawn_location else {}
                }
                new_nodes.append(new_node)
                print(f"  ✅ Spawning {spawn_info['class_name']} (ID: {next_id}) at {spawn_location['class_name'] if spawn_location else 'kitchen'}")
                next_id += 1
            else:
                print(f"  ⚠️  No spawn mapping for '{obj}' - skipping")

        # Create expanded scene graph
        if new_nodes:
            expanded_graph = {
                'nodes': scene_graph['nodes'] + new_nodes,
                'edges': scene_graph['edges']
            }

            # Use VirtualHome's expand_scene to add objects
            try:
                success, message = self.comm.expand_scene(expanded_graph)
                if success:
                    print(f"  ✅ Objects successfully spawned in VirtualHome")
                    return expanded_graph
                else:
                    print(f"  ⚠️  Failed to spawn objects: {message}")
                    return scene_graph
            except Exception as e:
                print(f"  ⚠️  Error spawning objects: {e}")
                return scene_graph

        return scene_graph
