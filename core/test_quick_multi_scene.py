#!/usr/bin/env python3
"""Quick test across multiple scenes - 3 tasks per scene, 3 scenes"""
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

def quick_multi_scene_test():
    """Quick test on 3 scenes with 3 diverse tasks each"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    # Test configuration: (scene_number, task_ids)
    test_config = [
        (1, [5, 50, 100]),  # Scene 1
        (2, [5, 50, 100]),  # Scene 2
        (3, [5, 50, 100]),  # Scene 3
    ]

    print("🏠 QUICK MULTI-SCENE TEST")
    print("=" * 70)
    print(f"Testing {sum(len(tasks) for _, tasks in test_config)} tasks across {len(test_config)} scenes")
    print("=" * 70)

    all_results = []

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for scene_num, task_ids in test_config:
            print(f"\n{'🏠' * 25} SCENE {scene_num} {'🏠' * 25}")

            # Update scene
            system.scene_name = f"TrimmedTestScene{scene_num}_graph"

            for task_id in task_ids:
                print(f"\n{'🎯' * 15} SCENE {scene_num} - TASK {task_id} {'🎯' * 15}")

                try:
                    success = system.run_complete_pipeline(task_id=task_id)
                    status = 'SUCCESS' if success else 'FAILED'

                    all_results.append({
                        'scene': scene_num,
                        'task_id': task_id,
                        'success': success,
                        'status': status
                    })

                    print(f"Result: {'✅' if success else '❌'} {status}")

                except Exception as e:
                    print(f"❌ Error: {e}")
                    all_results.append({
                        'scene': scene_num,
                        'task_id': task_id,
                        'success': False,
                        'status': f'ERROR: {str(e)[:50]}'
                    })

                print("-" * 70)

    # Summary
    print(f"\n{'=' * 70}")
    print("📊 RESULTS SUMMARY")
    print("=" * 70)

    for scene_num in sorted(set(r['scene'] for r in all_results)):
        scene_tasks = [r for r in all_results if r['scene'] == scene_num]
        successful = sum(1 for r in scene_tasks if r['success'])
        total = len(scene_tasks)
        print(f"Scene {scene_num}: {successful}/{total} ({100*successful/total:.0f}%)")

    total_successful = sum(1 for r in all_results if r['success'])
    total_tasks = len(all_results)
    print(f"\nOverall: {total_successful}/{total_tasks} ({100*total_successful/total_tasks:.1f}%)")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    print("Starting quick multi-scene test...\n")
    results = quick_multi_scene_test()
    print(f"\n✅ Test completed!")