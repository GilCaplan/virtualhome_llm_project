#!/usr/bin/env python3
"""Test system on tasks that should be reliably solvable"""
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

def test_reliable_tasks():
    """Test on tasks with objects that definitely exist and are interactable"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    # Tasks that should work based on capability analysis:
    # - Simple navigation tasks
    # - Tasks with common objects (fridge, bed, chair, computer)
    # - Tasks without complex object requirements
    reliable_tasks = [
        67,   # Wash teeth - just walk to bathroom
        50,   # Browse internet - computer, keyboard, chair all exist
        100,  # Work - sit, computer, mouse all exist
        238,  # Pet cat - cat exists and is grabbable
        250,  # Go to toilet - toilet exists
        281,  # Work - computer tasks
    ]

    print("🎯 TESTING RELIABLE TASKS")
    print("=" * 70)
    print(f"Testing {len(reliable_tasks)} tasks expected to succeed")
    print("=" * 70)

    results = []

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for task_id in reliable_tasks:
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
                print(f"\n❌ Error: {e}")
                results.append({
                    'task_id': task_id,
                    'success': False,
                    'status': f'ERROR: {str(e)[:100]}'
                })

            print("-" * 70)

    # Summary
    print(f"\n{'=' * 70}")
    print("📊 RESULTS")
    print("=" * 70)

    for result in results:
        print(f"Task {result['task_id']}: {result['status']}")

    successful = sum(1 for r in results if r['success'])
    total = len(results)
    print(f"\nSuccess Rate: {successful}/{total} ({100*successful/total:.1f}%)")
    print("=" * 70)

    return results

if __name__ == "__main__":
    print("Testing on reliable tasks...\n")
    results = test_reliable_tasks()
    print(f"\n✅ Test completed!")