#!/usr/bin/env python3

import sys
import os
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '../virtualhome/virtualhome/simulation'))
from unity_simulator import comm_unity

def diagnose_apartment_setup():
    """Diagnose and explain what objects are available in the apartment"""
    comm = comm_unity.UnityCommunication(
        file_name=os.path.join(os.path.dirname(__file__), '..', 'macos_exec.2.2.4.app'),
        port="8080"
    )

    print("=== VirtualHome Apartment Diagnosis ===")
    print("This tool shows what objects are available in the apartment for task execution.\n")

    # Reset and load scene
    comm.reset(0)

    # Load task scene graph (like the working algorithm)
    task_file = os.path.join(os.path.dirname(__file__), "..", "virtualhome/virtualhome/dataset/programs_processed_precond_nograb_morepreconds/init_and_final_graphs/TrimmedTestScene1_graph/results_intentions_march-13-18/file1003_2.json")

    if os.path.exists(task_file):
        with open(task_file, 'r') as f:
            graphs = json.load(f)
            initial_graph = graphs['init_graph']

        comm.expand_scene(initial_graph)
        print("✅ Loaded task-specific apartment layout")
    else:
        print("❌ Could not load apartment layout")
        return

    comm.add_character('Chars/Male2', initial_room='kitchen')
    print("✅ Added character in kitchen")

    # Get scene graph
    success, graph = comm.environment_graph()
    if not success:
        print("❌ Failed to get apartment layout")
        return

    print(f"\n🏠 APARTMENT OVERVIEW")
    print(f"Total objects in apartment: {len(graph['nodes'])}")

    # Categorize objects for explanation
    rooms = []
    furniture = []
    appliances = []
    small_objects = []

    for node in graph['nodes']:
        obj_class = node['class_name'].lower()
        obj_id = node['id']
        states = node.get('states', [])

        if any(room in obj_class for room in ['kitchen', 'bedroom', 'bathroom', 'living', 'dining', 'office']):
            rooms.append((obj_class, obj_id, states))
        elif any(furn in obj_class for furn in ['chair', 'desk', 'table', 'bed', 'sofa']):
            furniture.append((obj_class, obj_id, states))
        elif any(app in obj_class for app in ['computer', 'fridge', 'stove', 'microwave', 'tv', 'cpuscreen']):
            appliances.append((obj_class, obj_id, states))
        elif any(item in obj_class for item in ['keyboard', 'mouse', 'book', 'plate', 'cup', 'door']):
            small_objects.append((obj_class, obj_id, states))

    print(f"\n🏠 ROOMS & AREAS ({len(rooms)}):")
    for obj, obj_id, states in rooms[:8]:
        print(f"  • {obj.title().replace('_', ' ')} (ID: {obj_id})")
    if len(rooms) > 8:
        print(f"  ... and {len(rooms) - 8} more rooms")

    print(f"\n🪑 FURNITURE ({len(furniture)}):")
    for obj, obj_id, states in furniture[:8]:
        print(f"  • {obj.title().replace('_', ' ')} (ID: {obj_id})")
    if len(furniture) > 8:
        print(f"  ... and {len(furniture) - 8} more furniture items")

    print(f"\n📱 APPLIANCES & ELECTRONICS ({len(appliances)}):")
    for obj, obj_id, states in appliances[:8]:
        print(f"  • {obj.title().replace('_', ' ')} (ID: {obj_id})")
    if len(appliances) > 8:
        print(f"  ... and {len(appliances) - 8} more appliances")

    print(f"\n🔧 INTERACTIVE OBJECTS ({len(small_objects)}):")
    for obj, obj_id, states in small_objects[:8]:
        print(f"  • {obj.title().replace('_', ' ')} (ID: {obj_id})")
    if len(small_objects) > 8:
        print(f"  ... and {len(small_objects) - 8} more objects")

    # Show object mapping like our working algorithm
    print(f"\n🎯 OBJECT MAPPING (for task execution):")
    object_type_map = {}
    for node in graph['nodes']:
        obj_class = node['class_name'].lower()
        obj_id = node['id']

        if 'chair' in obj_class and 'chair' not in object_type_map:
            object_type_map['chair'] = obj_id
        elif ('computer' in obj_class or 'cpuscreen' in obj_class) and 'computer' not in object_type_map:
            object_type_map['computer'] = obj_id
        elif 'keyboard' in obj_class and 'keyboard' not in object_type_map:
            object_type_map['keyboard'] = obj_id
        elif 'mouse' in obj_class and 'mouse' not in object_type_map:
            object_type_map['mouse'] = obj_id
        elif 'desk' in obj_class and 'desk' not in object_type_map:
            object_type_map['desk'] = obj_id
        elif 'bedroom' in obj_class and 'bedroom' not in object_type_map:
            object_type_map['bedroom'] = obj_id
        elif 'fridge' in obj_class and 'fridge' not in object_type_map:
            object_type_map['fridge'] = obj_id

    for obj_type, obj_id in object_type_map.items():
        print(f"  • {obj_type.title()} → ID {obj_id}")

    print(f"\n📝 EXPLANATION:")
    print("• The apartment has multiple rooms (bedroom, kitchen, etc.)")
    print("• Each object has a unique ID that the algorithm uses")
    print("• The task solver maps generic object names to specific IDs")
    print("• This allows the agent to interact with the right objects")

    print(f"\n🎮 TASK CAPABILITIES:")
    print("• Email writing (computer, chair, keyboard)")
    print("• Food preparation (kitchen appliances)")
    print("• Navigation (rooms, doors)")
    print("• Object manipulation (grab, sit, open, close)")

    comm.close()

def main():
    print("🔍 VirtualHome Apartment Diagnostic Tool")
    print("=" * 50)

    try:
        diagnose_apartment_setup()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure VirtualHome simulator is available")

    print("\n" + "=" * 50)
    print("💡 This shows what objects are available for task execution")
    print("💡 The task solver uses this information to map actions to real objects")

if __name__ == "__main__":
    main()