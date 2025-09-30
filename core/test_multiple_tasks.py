#!/usr/bin/env python3

import os
import sys
from pddl_virtualhome_system import PDDLVirtualHomeSystem

def test_multiple_tasks():
    """Test the PDDL system on multiple tasks to verify generalization"""

    api_key = 'AIzaSyDlNUlJOXiH_30MvY-mmSpWLVsezTG3kMQ'
    simulator_path = '../macos_exec.2.2.4.app'

    # Test on more tasks for comprehensive generalization verification
    tasks_to_test = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    print("🤖 TESTING PDDL SYSTEM GENERALIZATION")
    print("=" * 60)
    print(f"Testing tasks: {tasks_to_test}")
    print("=" * 60)

    results = []

    for task_id in tasks_to_test:
        print(f"\n{'🔥' * 20} TASK {task_id} {'🔥' * 20}")

        try:
            # Create new system instance for each task
            system = PDDLVirtualHomeSystem(simulator_path, api_key)

            # Run the complete pipeline
            success = system.run_complete_pipeline(task_id=task_id)

            results.append({
                'task_id': task_id,
                'success': success,
                'status': 'SUCCESS' if success else 'FAILED'
            })

            print(f"Task {task_id} Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

        except Exception as e:
            print(f"❌ Task {task_id} Error: {e}")
            results.append({
                'task_id': task_id,
                'success': False,
                'status': f'ERROR: {e}',
                'error': str(e)
            })

        print("-" * 60)

    # Summary
    print(f"\n{'=' * 60}")
    print("📊 GENERALIZATION TEST RESULTS")
    print("=" * 60)

    successful_tasks = 0
    for result in results:
        task_id = result['task_id']
        status = result['status']
        print(f"Task {task_id}: {status}")
        if result['success']:
            successful_tasks += 1

    success_rate = (successful_tasks / len(results)) * 100
    print(f"\nOverall Success Rate: {successful_tasks}/{len(results)} ({success_rate:.1f}%)")

    print(f"\n💡 Generated Videos:")
    for result in results:
        if result['success']:
            task_id = result['task_id']
            video_path = f"core/Output/pddl_task_{task_id}_*.mp4"
            print(f"  • Task {task_id}: {video_path}")

    print("=" * 60)

    return results

if __name__ == "__main__":
    print("Starting multi-task generalization test...")
    results = test_multiple_tasks()

    print(f"\n🎯 Test completed!")
    print("This demonstrates PDDL system generalization across different task types.")