#!/usr/bin/env python3
"""Quick test of single task with new directory structure"""

import os
from pathlib import Path
from pddl_virtualhome_system_modular import PDDLVirtualHomeSystem

# Load environment
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

api_key = os.getenv('GOOGLE_API_KEY')
simulator_path = '../macos_exec.2.2.4.app'

print("Testing Task 67 with new directory structure...")
print("=" * 80)

system = PDDLVirtualHomeSystem(simulator_path, api_key)
result = system.run_complete_pipeline(task_id=67)
system.cleanup()

print("\n" + "=" * 80)
print("RESULT:")
print(f"  execution_success: {result.get('execution_success')}")
print(f"  video_generated: {result.get('video_generated')}")
print("=" * 80)

# Check output directory
output_dir = "Output/task_67"
if os.path.exists(output_dir):
    print(f"\nFiles in {output_dir}:")
    for f in os.listdir(output_dir):
        size = os.path.getsize(os.path.join(output_dir, f))
        print(f"  - {f} ({size} bytes)")
else:
    print(f"\n{output_dir} does not exist!")
