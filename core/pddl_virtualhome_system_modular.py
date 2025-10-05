#!/usr/bin/env python3
"""
Modular PDDL-VirtualHome System
Complete integration of all PDDL system modules
"""

import os
import sys
import google.generativeai as genai

# Import all modules from pddl_system package
from pddl_system import (
    SceneLoader,
    PDDLGenerator,
    LLMPlanner,
    ScriptConverter,
    Executor,
    ObjectManager,
    VideoGenerator
)


class PDDLVirtualHomeSystem:
    """
    Complete PDDL-centric VirtualHome task solving system (Modular Architecture):
    1. Scene + Task → PDDL Problem
    2. LLM Solves PDDL Problem
    3. PDDL Solution → VirtualHome Script
    4. Execute + Verify (headless)
    5. Generate Video
    """

    def __init__(self, simulator_path, api_key, port=None, scene_name="TrimmedTestScene1_graph"):
        self.simulator_path = simulator_path
        self.api_key = api_key
        self.port = port
        self.scene_name = scene_name
        self.current_task_id = None

        # Validate inputs
        if not api_key:
            raise ValueError("API key is required")

        if not os.path.exists(simulator_path):
            raise FileNotFoundError(f"Simulator not found at: {simulator_path}")

        # Ensure core/Output directory exists
        core_output_dir = os.path.join(os.path.dirname(__file__), 'Output')
        os.makedirs(core_output_dir, exist_ok=True)

        # Configure Gemini 1.5 Flash
        genai.configure(api_key=api_key)

        # Find available Flash model
        models = genai.list_models()
        available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]

        flash_model = None
        for model_name in available_models:
            if 'flash' in model_name.lower():
                flash_model = model_name
                break

        if flash_model:
            self.model = genai.GenerativeModel(flash_model)
            print(f"✅ Using {flash_model}")
        else:
            self.model = genai.GenerativeModel(available_models[0])
            print(f"✅ Using fallback model: {available_models[0]}")

        # Initialize all modules
        self.scene_loader = SceneLoader(simulator_path, scene_name)
        self.pddl_generator = PDDLGenerator()
        self.llm_planner = None  # Initialize after we have scene objects
        self.script_converter = None  # Initialize after we have comm
        self.executor = None  # Initialize after we have comm
        self.object_manager = None  # Initialize after we have comm
        self.video_generator = VideoGenerator()

    def run_complete_pipeline(self, task_id=0):
        """Run the complete PDDL-centric pipeline"""
        self.current_task_id = task_id
        print(f"PDDL-VIRTUALHOME PIPELINE (MODULAR) - TASK {task_id}")
        print("=" * 60)

        try:
            # Step 1: Load scene and task
            task = self.scene_loader.load_scene_and_task(task_id)

            # Step 2: Convert to PDDL problem
            scene_graph = self.scene_loader.initialize_or_reuse_simulator(task)
            pddl_problem = self.pddl_generator.scene_to_pddl_problem(task, scene_graph)

            # Initialize modules that need comm connection
            if self.script_converter is None:
                self.script_converter = ScriptConverter(self.scene_loader.comm)
            if self.executor is None:
                self.executor = Executor(self.scene_loader.comm, self.model)
            if self.object_manager is None:
                self.object_manager = ObjectManager(self.scene_loader.comm)

            # Step 3: Solve with LLM
            if self.llm_planner is None:
                self.llm_planner = LLMPlanner(
                    self.model,
                    self.pddl_generator.current_scene_objects,
                    PDDLGenerator.VIRTUALHOME_DOMAIN
                )
            else:
                # Update scene objects for current task
                self.llm_planner.scene_objects = self.pddl_generator.current_scene_objects

            pddl_solution = self.llm_planner.solve_pddl_with_llm(pddl_problem, task)

            # Step 4: Convert to VirtualHome script
            # Set current task ID in script converter for file naming
            self.script_converter.current_task_id = self.current_task_id
            vh_script = self.script_converter.pddl_to_virtualhome_script(pddl_solution)

            # Step 4.5: Detect and spawn missing objects
            missing_objects = self.object_manager._detect_missing_objects(vh_script, task['initial_graph'])
            if missing_objects:
                updated_graph = self.object_manager._spawn_missing_objects(
                    missing_objects, task['initial_graph'], task
                )
                if updated_graph != task['initial_graph']:
                    task['initial_graph'] = updated_graph
                    # Refresh object mapping with spawned objects
                    vh_script = self.script_converter.pddl_to_virtualhome_script(pddl_solution)

            # Step 5: Execute and verify
            success, verification = self.executor.execute_and_verify(vh_script, task)

            # Step 6: Generate video
            output_base_dir = os.path.join(os.path.dirname(__file__), 'Output')
            video_success = self.video_generator.generate_video(task, output_base_dir)

            # Final result
            print("\n" + "=" * 60)
            print("FINAL RESULT:")
            print(f"Task: {task['title']}")
            print(f"Execution: {'SUCCESS' if success else 'FAILED'}")
            print(f"Verification: {verification}")
            print(f"Video: {'GENERATED' if video_success else 'FAILED'}")
            print("=" * 60)

            return {
                'execution_success': success,
                'verification': verification,
                'video_generated': video_success,
                'task_id': task['id'],
                'task_title': task['title']
            }

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'execution_success': False,
                'error': str(e),
                'task_id': task_id if 'task' not in locals() else task['id']
            }

    def cleanup(self):
        """Explicit cleanup method"""
        print("Cleaning up resources...")
        if self.scene_loader:
            self.scene_loader.cleanup()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup"""
        self.cleanup()
        return False

    def __del__(self):
        """Destructor - final cleanup attempt"""
        if hasattr(self, 'scene_loader') and self.scene_loader:
            try:
                self.scene_loader.cleanup()
            except:
                pass


def main():
    """Test the modular PDDL-VirtualHome system"""
    # Try to load from .env file automatically
    try:
        from dotenv import load_dotenv
        from pathlib import Path
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            print(f"Loaded environment from {env_path}")
    except ImportError:
        print("python-dotenv not installed. Install with: pip install python-dotenv")
        print("Falling back to environment variables...")

    # Load API key from environment
    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        raise ValueError(
            "GOOGLE_API_KEY environment variable not set.\n"
            "Please either:\n"
            "  1. Install python-dotenv: pip install python-dotenv\n"
            "  2. Set manually: export GOOGLE_API_KEY='your-api-key'\n"
            "  3. Add to .env file in project root\n"
            "Get your API key from: https://makersuite.google.com/app/apikey"
        )

    simulator_path = os.path.join(os.path.dirname(__file__), '..', 'macos_exec.2.2.4.app')

    if not os.path.exists(simulator_path):
        raise FileNotFoundError(
            f"VirtualHome simulator not found at: {simulator_path}\n"
            f"Please ensure the simulator is installed."
        )

    # Use context manager for automatic cleanup
    with PDDLVirtualHomeSystem(simulator_path, api_key) as system:
        success = system.run_complete_pipeline(task_id=0)
        print(f"\nPipeline completed: {'SUCCESS' if success else 'FAILED'}")


if __name__ == "__main__":
    main()
