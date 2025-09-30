#!/usr/bin/env python3

import os
import sys
from pathlib import Path
from pddl_virtualhome_system import PDDLVirtualHomeSystem

# Try to load from .env file automatically
try:
    from dotenv import load_dotenv
    # Load from parent directory (where .env is located)
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Loaded environment from {env_path}")
except ImportError:
    print("⚠️  python-dotenv not installed. Install with: pip install python-dotenv")
    print("   Falling back to environment variables...")

def test_multiple_tasks():
    """Test the PDDL system on multiple tasks to verify generalization"""

    # Load API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set.\n"
            "Please either:\n"
            "  1. Install python-dotenv: pip install python-dotenv\n"
            "  2. Set manually: export GOOGLE_API_KEY='your-api-key'\n"
            "  3. Add to .env file in project root"
        )

    simulator_path = '../macos_exec.2.2.4.app'

    if not os.path.exists(simulator_path):
        raise FileNotFoundError(f"Simulator not found at: {simulator_path}")

    # Test 20 random tasks for comprehensive verification
    tasks_to_test = [25, 27, 30, 32, 89, 95, 104, 114, 142, 203, 223, 225, 228, 238, 250, 281, 429, 432, 459, 517]

    print("🤖 TESTING PDDL SYSTEM ON 20 RANDOM TASKS")
    print("=" * 60)
    print(f"Testing tasks: {tasks_to_test}")
    print("=" * 60)

    results = []

    # Use single system instance for all tasks (enables simulator reuse)
    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for task_id in tasks_to_test:
            print(f"\n{'🔥' * 20} TASK {task_id} {'🔥' * 20}")

            try:
                # Run the complete pipeline with simulator reuse
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
    print("Starting 20-task random generalization test...")
    results = test_multiple_tasks()

    print(f"\n🎯 Test completed!")
    print("This demonstrates PDDL system generalization across diverse tasks.")