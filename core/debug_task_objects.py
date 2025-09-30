#!/usr/bin/env python3
"""Debug script to check what objects exist in failing tasks"""
import os
import sys
from pathlib import Path

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

from pddl_virtualhome_system import PDDLVirtualHomeSystem

def analyze_task_objects(task_id, expected_objects):
    """Analyze what objects exist in a task scene"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        task = system.load_scene_and_task(task_id)
        scene_graph = task['initial_graph']

        print(f"\n{'='*70}")
        print(f"TASK {task_id}: {task['title']}")
        print(f"Description: {task['description']}")
        print(f"{'='*70}")

        # Search for expected objects
        found_objects = {}
        all_objects = []

        for node in scene_graph['nodes']:
            class_name = node['class_name'].lower()
            node_id = node['id']
            properties = node.get('properties', [])
            states = node.get('states', [])
            category = node.get('category', 'N/A')

            all_objects.append(class_name)

            # Check if any expected object matches
            for expected in expected_objects:
                if expected.lower() in class_name:
                    if expected not in found_objects:
                        found_objects[expected] = []
                    found_objects[expected].append({
                        'class_name': node['class_name'],
                        'id': node_id,
                        'properties': properties,
                        'states': states,
                        'category': category
                    })

        # Report findings
        print(f"\n🔍 SEARCHING FOR: {', '.join(expected_objects)}")
        print(f"\n📊 RESULTS:")

        for expected in expected_objects:
            if expected in found_objects:
                print(f"\n✅ FOUND '{expected}':")
                for obj in found_objects[expected]:
                    print(f"  • {obj['class_name']} (ID: {obj['id']})")
                    print(f"    Properties: {obj['properties']}")
                    print(f"    States: {obj['states']}")
                    print(f"    Category: {obj['category']}")

                    # Assess interactability
                    interactable = any(prop in obj['properties'] for prop in
                                     ['GRABBABLE', 'CAN_OPEN', 'HAS_SWITCH', 'SITTABLE', 'LOOKABLE'])
                    print(f"    Interactable: {'YES' if interactable else 'NO (no interactive properties)'}")
            else:
                print(f"\n❌ NOT FOUND: '{expected}'")
                # Show similar objects
                similar = [obj for obj in all_objects if expected[:3] in obj or obj[:3] in expected]
                if similar:
                    print(f"  Similar objects in scene: {', '.join(set(similar[:5]))}")

        print(f"\n📈 Total objects in scene: {len(scene_graph['nodes'])}")
        print("="*70)

if __name__ == "__main__":
    # Analyze failing tasks
    tasks = [
        (25, ['book', 'light', 'lamp']),
        (27, ['light', 'lamp', 'outlet']),
        (30, ['glasses', 'book']),
        (89, ['coffeemaker', 'coffee']),
        (104, ['desk', 'computer', 'chair']),
        (114, ['tv', 'remote']),
        (142, ['phone', 'cellphone']),
        (203, ['water', 'glass', 'cup']),
    ]

    for task_id, expected_objects in tasks:
        try:
            analyze_task_objects(task_id, expected_objects)
        except Exception as e:
            print(f"\n❌ ERROR analyzing task {task_id}: {e}")
            print("="*70)