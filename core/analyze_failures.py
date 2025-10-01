#!/usr/bin/env python3
"""Analyze common failure patterns in VirtualHome execution"""
import os
import sys
from pathlib import Path
from pddl_virtualhome_system import PDDLVirtualHomeSystem

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

def analyze_object_reachability(task_id):
    """Analyze which objects in a scene are actually reachable by VirtualHome"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        # Load task
        task = system.load_scene_and_task(task_id)
        scene_graph = task['initial_graph']

        print(f"\n{'='*70}")
        print(f"TASK {task_id}: {task['title']}")
        print(f"Description: {task['description']}")
        print(f"{'='*70}")

        # Get capabilities
        capabilities = system._build_object_capabilities(scene_graph)

        # Categorize objects by property
        by_property = {}
        for obj_name, caps in capabilities.items():
            for prop in caps['properties']:
                if prop not in by_property:
                    by_property[prop] = []
                by_property[prop].append(obj_name)

        print(f"\n📊 OBJECTS BY PROPERTY:")
        for prop in sorted(by_property.keys()):
            objects = by_property[prop]
            print(f"\n{prop}: ({len(objects)} objects)")
            print(f"  {', '.join(objects[:10])}")
            if len(objects) > 10:
                print(f"  ... and {len(objects) - 10} more")

        # Check for common failure objects
        failure_objects = ['groceries', 'book', 'ceilinglamp', 'plate', 'chair', 'sofa']
        print(f"\n🔍 CHECKING COMMON FAILURE OBJECTS:")
        for obj in failure_objects:
            matches = [name for name in capabilities.keys() if obj in name.lower()]
            if matches:
                print(f"\n✅ '{obj}' found as: {', '.join(matches[:5])}")
                for match in matches[:3]:
                    cap = capabilities[match]
                    print(f"   {match}: {cap['properties']} -> {', '.join(cap['actions'][:5])}")
            else:
                print(f"\n❌ '{obj}' NOT FOUND in scene")

        # Count objects by category
        print(f"\n📈 SUMMARY:")
        print(f"Total interactable objects: {len(capabilities)}")
        print(f"Total properties represented: {len(by_property)}")
        print(f"Total nodes in scene graph: {len(scene_graph['nodes'])}")

        return capabilities

def test_simple_actions(task_id):
    """Test simple, basic actions that should always work"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    print(f"\n{'='*70}")
    print(f"TESTING SIMPLE ACTIONS ON TASK {task_id}")
    print(f"{'='*70}")

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        task = system.load_scene_and_task(task_id)

        # Test 1: Just walk to a room
        print(f"\n🧪 TEST 1: Walk to bedroom")
        simple_script = [
            "<char0> [WALK] <bedroom> (74)"
        ]

        try:
            system._initialize_simulator()
            system.comm.render_script(simple_script, recording=True, find_solution=True)
            print("✅ Simple walk succeeded")
        except Exception as e:
            print(f"❌ Simple walk failed: {e}")

        # Test 2: Find an object
        print(f"\n🧪 TEST 2: Find fridge")
        simple_script2 = [
            "<char0> [WALK] <kitchen> (207)",
            "<char0> [FIND] <fridge> (306)"
        ]

        try:
            system._initialize_simulator()
            system.comm.render_script(simple_script2, recording=True, find_solution=True)
            print("✅ Find object succeeded")
        except Exception as e:
            print(f"❌ Find object failed: {e}")

        # Test 3: Open/close fridge
        print(f"\n🧪 TEST 3: Open and close fridge")
        simple_script3 = [
            "<char0> [WALK] <kitchen> (207)",
            "<char0> [FIND] <fridge> (306)",
            "<char0> [OPEN] <fridge> (306)",
            "<char0> [CLOSE] <fridge> (306)"
        ]

        try:
            system._initialize_simulator()
            system.comm.render_script(simple_script3, recording=True, find_solution=True)
            print("✅ Open/close succeeded")
        except Exception as e:
            print(f"❌ Open/close failed: {e}")

if __name__ == "__main__":
    # Analyze a few problematic tasks
    problem_tasks = [1, 25, 67]

    for task_id in problem_tasks:
        try:
            print(f"\n{'#'*70}")
            print(f"# ANALYZING TASK {task_id}")
            print(f"{'#'*70}")
            analyze_object_reachability(task_id)
        except Exception as e:
            print(f"❌ Error analyzing task {task_id}: {e}")

    # Test simple actions
    print(f"\n{'#'*70}")
    print(f"# TESTING BASIC ACTION EXECUTION")
    print(f"{'#'*70}")
    try:
        test_simple_actions(1)
    except Exception as e:
        print(f"❌ Error testing simple actions: {e}")

    print(f"\n{'='*70}")
    print("Analysis complete!")