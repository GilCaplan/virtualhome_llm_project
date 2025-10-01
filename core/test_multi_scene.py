#!/usr/bin/env python3
"""Test PDDL system across multiple scenes and diverse tasks"""
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

def test_across_scenes():
    """Test system on multiple scenes with diverse task categories"""
    api_key = os.getenv('GOOGLE_API_KEY')
    simulator_path = '../macos_exec.2.2.4.app'

    # Test configuration: (scene_number, task_ids)
    # Sample diverse tasks from different categories across multiple scenes
    test_config = [
        # Scene 1 - current scene (already tested)
        (1, [10, 50, 100, 150, 200]),

        # Scene 2 - different layout
        (2, [15, 45, 95, 145, 195]),

        # Scene 3 - variation
        (3, [20, 60, 110, 160, 210]),

        # Scene 4
        (4, [25, 65, 115, 165, 215]),

        # Scene 5
        (5, [30, 70, 120, 170, 220]),
    ]

    print("🏠 MULTI-SCENE GENERALIZATION TEST")
    print("=" * 70)
    print(f"Testing {sum(len(tasks) for _, tasks in test_config)} tasks across {len(test_config)} scenes")
    print("=" * 70)

    all_results = []
    scene_summaries = []

    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        for scene_num, task_ids in test_config:
            print(f"\n{'🏠' * 30}")
            print(f"TESTING SCENE {scene_num}: TrimmedTestScene{scene_num}_graph")
            print(f"{'🏠' * 30}")

            # Update scene in the system
            scene_name = f"TrimmedTestScene{scene_num}_graph"
            system.scene_name = scene_name

            scene_results = []

            for task_id in task_ids:
                print(f"\n{'🎯' * 20} SCENE {scene_num} - TASK {task_id} {'🎯' * 20}")

                try:
                    success = system.run_complete_pipeline(task_id=task_id)

                    scene_results.append({
                        'scene': scene_num,
                        'task_id': task_id,
                        'success': success,
                        'status': 'SUCCESS' if success else 'FAILED'
                    })

                    print(f"Scene {scene_num}, Task {task_id}: {'✅ SUCCESS' if success else '❌ FAILED'}")

                except Exception as e:
                    print(f"❌ Scene {scene_num}, Task {task_id} Error: {e}")
                    scene_results.append({
                        'scene': scene_num,
                        'task_id': task_id,
                        'success': False,
                        'status': f'ERROR: {str(e)[:50]}'
                    })

                print("-" * 70)

            # Scene summary
            successful = sum(1 for r in scene_results if r['success'])
            total = len(scene_results)
            success_rate = (successful / total * 100) if total > 0 else 0

            scene_summaries.append({
                'scene': scene_num,
                'successful': successful,
                'total': total,
                'rate': success_rate
            })

            all_results.extend(scene_results)

            print(f"\n📊 SCENE {scene_num} SUMMARY: {successful}/{total} ({success_rate:.1f}%)")
            print("=" * 70)

    # Overall summary
    print(f"\n{'=' * 70}")
    print("🌍 OVERALL MULTI-SCENE TEST RESULTS")
    print("=" * 70)

    for summary in scene_summaries:
        print(f"Scene {summary['scene']}: {summary['successful']}/{summary['total']} ({summary['rate']:.1f}%)")

    total_successful = sum(s['successful'] for s in scene_summaries)
    total_tasks = sum(s['total'] for s in scene_summaries)
    overall_rate = (total_successful / total_tasks * 100) if total_tasks > 0 else 0

    print(f"\nOverall Success Rate: {total_successful}/{total_tasks} ({overall_rate:.1f}%)")
    print("=" * 70)

    # Detailed results
    print(f"\n📝 DETAILED RESULTS BY SCENE:")
    for scene_num in sorted(set(r['scene'] for r in all_results)):
        print(f"\nScene {scene_num}:")
        scene_tasks = [r for r in all_results if r['scene'] == scene_num]
        for result in scene_tasks:
            print(f"  Task {result['task_id']}: {result['status']}")

    print("=" * 70)

    return all_results, scene_summaries

if __name__ == "__main__":
    print("Starting multi-scene generalization test...")
    print("This will test the PDDL system across 5 different VirtualHome scenes")
    print("with 5 tasks per scene (25 tasks total)\n")

    results, summaries = test_across_scenes()

    print(f"\n✅ Multi-scene test completed!")
    print("This demonstrates PDDL system generalization across different environments.")