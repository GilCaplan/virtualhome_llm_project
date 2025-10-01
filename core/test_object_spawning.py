#!/usr/bin/env python3
"""Test dynamic object spawning on tasks with missing objects"""
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

def test_object_spawning():
    """Test on tasks that failed due to missing objects"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    # Tasks that previously failed due to missing objects:
    # Task 1: groceries
    # Task 25: book
    # Task 5: plate/dishwasher
    missing_object_tasks = [1, 25, 5]

    print("🎨 TESTING DYNAMIC OBJECT SPAWNING")
    print("=" * 70)
    print(f"Testing {len(missing_object_tasks)} tasks with known missing objects")
    print("=" * 70)

    results = []

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for task_id in missing_object_tasks:
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
    print("📊 OBJECT SPAWNING TEST RESULTS")
    print("=" * 70)

    for result in results:
        print(f"Task {result['task_id']}: {result['status']}")

    successful = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\nSuccess Rate: {successful}/{total} ({100*successful/total:.1f}%)")
    print("=" * 70)

    return results

if __name__ == "__main__":
    print("Testing dynamic object spawning...\n")
    results = test_object_spawning()
    print(f"\n✅ Test completed!")