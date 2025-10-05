#!/usr/bin/env python3
"""Scene and task loading module"""

import os
import sys
import json
import glob
import socket
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '../../virtualhome/virtualhome/simulation'))
from unity_simulator import comm_unity


class SceneLoader:
    """Handles loading VirtualHome scenes and tasks"""

    def __init__(self, simulator_path, scene_name="TrimmedTestScene1_graph"):
        self.simulator_path = simulator_path
        self.scene_name = scene_name
        self.comm = None
        self.port = None

        if not os.path.exists(simulator_path):
            raise FileNotFoundError(f"Simulator not found at: {simulator_path}")

    def load_scene_and_task(self, task_id=0):
        """Load VirtualHome scene and task"""
        print(f"Step 1: Loading scene and task {task_id}")

        # Validate task_id
        if not isinstance(task_id, int):
            raise TypeError(f"task_id must be integer, got {type(task_id).__name__}")

        if task_id < 0:
            raise ValueError(f"task_id must be non-negative, got {task_id}")

        # Load tasks from dataset
        scene_name = self.scene_name
        base_path = os.path.join(os.path.dirname(__file__), '../..',
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
            'task_id': task_id,
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

    def get_available_port(self, start_port=8080, max_attempts=10):
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

    def initialize_or_reuse_simulator(self, task):
        """Initialize simulator if needed, or reuse existing one"""
        # Get available port (only once per instance)
        if not self.port:
            self.port = self.get_available_port()
            print(f"  Using simulator port: {self.port}")

        # DISABLED: Simulator reuse causes "Max frame number exceeded" errors
        # Force fresh restart for each task to reset recorder buffer
        if self.comm is not None:
            print(f"  Restarting simulator to reset recorder buffer...")
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

                # Increase timeout for complex tasks (default is 30s)
                self.comm.timeout_wait = 240

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
                else:
                    raise RuntimeError(f"Failed to initialize simulator after {max_retries} attempts")

        # If we get here, all retries failed
        raise RuntimeError(f"Failed to initialize simulator after {max_retries} attempts")

    def cleanup(self):
        """Close simulator connection"""
        if self.comm:
            try:
                self.comm.close()
            except:
                pass
            self.comm = None
