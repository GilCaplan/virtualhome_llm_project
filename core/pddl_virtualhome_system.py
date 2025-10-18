#!/usr/bin/env python3
"""
PDDL-VirtualHome System - Backward Compatibility Wrapper

This file maintains backward compatibility with existing code.
The implementation has been refactored into modular components in pddl_system/

For new code, use: from pddl_virtualhome_system_modular import PDDLVirtualHomeSystem
"""

import os
import sys
from pathlib import Path

from ENV_VARS import SIMULATOR_PATH, GEMINI_API_KEY
# Import the modular implementation
from pddl_virtualhome_system_modular import PDDLVirtualHomeSystem

# Re-export for backward compatibility
__all__ = ['PDDLVirtualHomeSystem']

# The old 1900-line implementation has been split into these modules:
# - pddl_system/scene_loader.py - Scene and task loading
# - pddl_system/pddl_generator.py - PDDL problem generation
# - pddl_system/llm_planner.py - LLM-based planning
# - pddl_system/script_converter.py - PDDL to VirtualHome conversion
# - pddl_system/executor.py - Script execution and verification
# - pddl_system/object_manager.py - Dynamic object spawning
# - pddl_system/video_generator.py - Video generation
#
# Main integration: pddl_virtualhome_system_modular.py
#
# Original 1890-line implementation backed up as: pddl_virtualhome_system_OLD_BACKUP.py


def main():
    """Run system with first scene and 4 default tasks"""

    # Load environment
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass

    # Configuration
    api_key = GEMINI_API_KEY
    simulator_path = SIMULATOR_PATH
    scene_name = 'TrimmedTestScene1_graph'
    # TODO - test on more tasks
    # default_tasks = [67, 1, 5, 36, 5]  # Wash teeth, Put groceries, Change TV channel, Watch TV
    default_tasks = [1]  # Wash teeth, Put groceries, Change TV channel, Watch TV


    print("=" * 80)
    print("PDDL-VIRTUALHOME SYSTEM - DEFAULT RUN")
    print("=" * 80)
    print(f"Scene: {scene_name}")
    print(f"Tasks: {default_tasks}")
    print("=" * 80)
    print()

    # Initialize system
    system = PDDLVirtualHomeSystem(simulator_path, api_key, scene_name=scene_name)

    # Run tasks
    results = {}
    for i, task_id in enumerate(default_tasks, 1):
        print()
        print("=" * 80)
        print(f"TASK {i}/{len(default_tasks)}: Task ID {task_id}")
        print("=" * 80)

        try:
            result = system.run_complete_pipeline(task_id=task_id)
            success = result.get('execution_success', False) if result else False
            results[task_id] = success

            if success:
                print(f"✅ Task {task_id}: SUCCESS")
            else:
                print(f"❌ Task {task_id}: FAILED")
        except Exception as e:
            print(f"❌ Task {task_id}: EXCEPTION - {str(e)[:100]}")
            results[task_id] = False

    # Cleanup
    system.cleanup()

    # Summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    successes = sum(1 for v in results.values() if v)
    total = len(results)
    success_rate = (successes / total * 100) if total > 0 else 0

    print(f"Total Tasks: {total}")
    print(f"Successes: {successes}")
    print(f"Failures: {total - successes}")
    print(f"Success Rate: {success_rate:.1f}%")
    print()

    for task_id, success in results.items():
        status = "✅" if success else "❌"
        print(f"  {status} Task {task_id}")

    print("=" * 80)


if __name__ == "__main__":
    main()
