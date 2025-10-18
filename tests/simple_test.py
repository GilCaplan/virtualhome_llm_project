#!/usr/bin/env python3

import sys
import os
import json

from ENV_VARS import SIMULATOR_PATH, DATASET_BASE_PATH

sys.path.append(os.path.join(os.path.dirname(__file__), '../virtualhome/virtualhome/simulation'))
from virtualhome.virtualhome.simulation.unity_simulator import comm_unity

# Simple test with PROPER scene setup like our working algorithm
comm = comm_unity.UnityCommunication(
    file_name=SIMULATOR_PATH,
    port="8080"
)

print("Setting up scene with task-specific graph...")
comm.reset(0)

# Load the SAME scene graph as our working algorithm
# TODO - change the url
task_file = DATASET_BASE_PATH + r"\init_and_final_graphs\TrimmedTestScene1_graph\results_intentions_march-13-18\file1003_2.json"
# task_file = os.path.join(os.path.dirname(__file__), "..", "virtualhome/virtualhome/dataset/programs_processed_precond_nograb_morepreconds/init_and_final_graphs/TrimmedTestScene1_graph/results_intentions_march-13-18/file1003_2.json")

with open(task_file, 'r') as f:
    graphs = json.load(f)
    initial_graph = graphs['init_graph']

comm.expand_scene(initial_graph)
comm.add_character('Chars/Male2', initial_room='kitchen')

print("Getting scene graph...")
success, graph = comm.environment_graph()
if success:
    # Find objects like our working algorithm
    object_type_map = {}
    for node in graph['nodes']:
        obj_class = node['class_name'].lower()
        obj_id = node['id']
        if 'chair' in obj_class:
            object_type_map['chair'] = obj_id
            break

    print(f"Found chair with ID: {object_type_map.get('chair', 'NOT FOUND')}")

    if 'chair' in object_type_map:
        # Use ACTUAL object ID like our working algorithm
        chair_id = object_type_map['chair']

        # Try with find_solution=True first (like our working algorithm)
        simple_script = [
            f'<char0> [FIND] <chair> ({chair_id})',
            f'<char0> [SIT] <chair> ({chair_id})',
        ]

        print(f"Testing with find_solution=True: {simple_script}")
        success, message = comm.render_script(
            simple_script,
            recording=True,
            find_solution=True,  # Let VirtualHome auto-find
            frame_rate=3,
            camera_mode=["PERSON_FROM_BACK"],
            file_name_prefix="simple_test_autofind"
        )

        print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
        print(f"Message: {message}")

        if not success:
            # Also try the generic approach
            print("\nTrying generic approach...")
            generic_script = [
                '<char0> [FIND] <chair> (1)',
                '<char0> [SIT] <chair> (1)',
            ]

            success2, message2 = comm.render_script(
                generic_script,
                recording=True,
                find_solution=True,
                frame_rate=3,
                camera_mode=["PERSON_FROM_BACK"],
                file_name_prefix="simple_test_generic"
            )

            print(f"Generic result: {'✅ SUCCESS' if success2 else '❌ FAILED'}")
            print(f"Generic message: {message2}")
    else:
        print("❌ No chair found in scene!")

# Close connection
comm.close()