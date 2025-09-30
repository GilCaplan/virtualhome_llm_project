#!/usr/bin/env python3
"""Test improved fuzzy matching on previously failing tasks"""
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

def test_fuzzy_improvements():
    """Test fuzzy matching improvements on problem tasks"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    # Focus on tasks with known object mismatches
    # Task 89: coffeemaker vs coffe_maker
    # Task 142: phone interaction
    # Task 203: water/glass/cup confusion
    # Task 25: book/light issues
    # Task 114: tv/remote issues
    test_tasks = [89, 142, 203, 25, 114]

    print("🔍 TESTING FUZZY MATCHING IMPROVEMENTS")
    print("=" * 70)
    print(f"Testing tasks with known object name mismatches: {test_tasks}")
    print("=" * 70)

    results = []

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for task_id in test_tasks:
            print(f"\n{'🎯' * 25} TASK {task_id} {'🎯' * 25}")

            try:
                success = system.run_complete_pipeline(task_id=task_id)

                results.append({
                    'task_id': task_id,
                    'success': success,
                    'status': 'SUCCESS' if success else 'FAILED'
                })

                print(f"Task {task_id}: {'✅ SUCCESS' if success else '❌ FAILED'}")

            except Exception as e:
                print(f"❌ Task {task_id} Error: {e}")
                results.append({
                    'task_id': task_id,
                    'success': False,
                    'status': f'ERROR: {e}'
                })

            print("-" * 70)

    # Summary
    print(f"\n{'=' * 70}")
    print("📊 FUZZY MATCHING TEST RESULTS")
    print("=" * 70)

    successful = sum(1 for r in results if r['success'])
    for result in results:
        print(f"Task {result['task_id']}: {result['status']}")

    print(f"\nSuccess Rate: {successful}/{len(results)} ({100*successful/len(results):.1f}%)")
    print("=" * 70)

    return results

if __name__ == "__main__":
    print("Testing fuzzy matching improvements on 5 problematic tasks...")
    results = test_fuzzy_improvements()
    print("\n✅ Test completed!")