#!/usr/bin/env python3
"""Test on tasks that haven't been checked yet"""
import os
import sys
import random
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

def test_unexplored_tasks():
    """Test on random tasks that haven't been tested yet"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    # Previously tested tasks to avoid
    tested = {1, 5, 10, 15, 20, 23, 25, 27, 28, 30, 32, 50, 67, 75, 89, 95, 98, 100, 104,
              114, 142, 150, 152, 200, 203, 223, 225, 228, 238, 250, 281, 429, 432, 459,
              486, 517, 548, 782}

    # Sample 15 random tasks from 0-800 that haven't been tested
    all_tasks = set(range(0, 800))
    untested = all_tasks - tested
    new_tasks = sorted(random.sample(list(untested), 15))

    print("🆕 TESTING UNEXPLORED TASKS")
    print("=" * 70)
    print(f"Testing {len(new_tasks)} tasks: {new_tasks}")
    print("=" * 70)

    results = []

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for task_id in new_tasks:
            print(f"\n{'='*60}")
            print(f"TASK {task_id}")
            print(f"{'='*60}")

            try:
                success = system.run_complete_pipeline(task_id=task_id)

                results.append({
                    'task_id': task_id,
                    'success': success,
                    'status': 'SUCCESS' if success else 'FAILED'
                })

                print(f"\nResult: {'✅ SUCCESS' if success else '❌ FAILED'}")

            except Exception as e:
                print(f"\n❌ Error: {str(e)[:200]}")
                results.append({
                    'task_id': task_id,
                    'success': False,
                    'status': f'ERROR'
                })

            print("-" * 70)

    # Summary
    print(f"\n{'=' * 70}")
    print("📊 UNEXPLORED TASKS RESULTS")
    print("=" * 70)

    for result in results:
        print(f"Task {result['task_id']}: {result['status']}")

    successful = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\nSuccess Rate: {successful}/{total} ({100*successful/total:.1f}%)")
    print("=" * 70)

    # Identify patterns
    successes = [r['task_id'] for r in results if r['success']]
    failures = [r['task_id'] for r in results if not r['success']]

    print(f"\n✅ Successful: {successes}")
    print(f"❌ Failed: {failures}")

    return results

if __name__ == "__main__":
    print("Testing on unexplored tasks...\n")
    random.seed(42)  # For reproducibility
    results = test_unexplored_tasks()
    print(f"\n✅ Test completed!")