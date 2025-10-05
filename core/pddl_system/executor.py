#!/usr/bin/env python3
"""
Executor Module

This module handles script execution, task verification, and adaptive replanning.
It executes VirtualHome scripts and verifies task completion through state comparison.
"""

import time
from requests.exceptions import ReadTimeout, ConnectionError


class Executor:
    """
    Executes VirtualHome scripts and verifies task completion.

    Handles:
    - Script execution with recording
    - Spatial constraint validation
    - Task completion verification
    - Adaptive replanning on failure
    """

    def __init__(self, comm, model):
        """
        Initialize the executor.

        Args:
            comm: VirtualHome simulator communication instance
            model: Google Generative AI model for replanning
        """
        self.comm = comm
        self.model = model

    def _retry_with_backoff(self, func, max_retries=3, initial_wait=2, *args, **kwargs):
        """
        Retry a function with exponential backoff on timeout/connection errors.

        Args:
            func: Function to retry
            max_retries: Maximum number of retry attempts
            initial_wait: Initial wait time in seconds
            *args, **kwargs: Arguments to pass to the function

        Returns:
            Result of the function call, or raises the last exception
        """
        wait_time = initial_wait
        last_exception = None

        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except (ReadTimeout, ConnectionError, Exception) as e:
                last_exception = e
                error_type = type(e).__name__

                if attempt < max_retries - 1:
                    print(f"  ⚠️  {error_type} on attempt {attempt + 1}/{max_retries}")
                    print(f"  Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                    wait_time *= 2  # Exponential backoff
                else:
                    print(f"  ❌ Failed after {max_retries} attempts")

        raise last_exception

    def execute_and_verify(self, vh_script, task):
        """
        Execute script and verify completion.

        Args:
            vh_script: List of VirtualHome script commands
            task: Task dictionary

        Returns:
            tuple: (success: bool, verification_message: str)
        """
        print("Step 5: Executing script and verifying completion")

        # Spatial validation before execution
        self._validate_spatial_constraints(vh_script)

        # Capture initial state with retry logic
        try:
            success, initial_graph = self._retry_with_backoff(
                self.comm.environment_graph,
                max_retries=3,
                initial_wait=2
            )
            if not success:
                print("Failed to capture initial state")
                return False, "Cannot capture initial state"
        except Exception as e:
            print(f"Error capturing initial state after retries: {e}")
            return False, f"Cannot capture initial state: {str(e)}"

        # Execute script with recording
        print(f"Executing {len(vh_script)} actions...")

        # Ensure Output directory exists
        import os
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Output')
        os.makedirs(output_dir, exist_ok=True)
        print(f"Saving frames to: {output_dir}")

        execution_success, message = self.comm.render_script(
            vh_script,
            recording=True,
            find_solution=True,
            frame_rate=3,
            camera_mode=["PERSON_FROM_BACK"],
            file_name_prefix=f"pddl_task_{task['id']}",
            output_folder=output_dir,  # Specify where to save frames
            processing_time_limit=300,
            skip_execution=False,
            image_synthesis=["normal"],  # Ensure image generation
            save_pose_data=False
        )

        if not execution_success:
            print(f"Execution failed: {message}")

            # Attempt adaptive replanning
            alternative_plan = self._analyze_failure_and_replan(str(message), vh_script, task)

            if alternative_plan:
                print("\n🔄 EXECUTING ALTERNATIVE PLAN...")
                try:
                    # Convert alternative PDDL plan to VH script
                    # Note: This requires ScriptConverter, so in practice we'd need to pass it
                    # For now, we'll just note that replanning is attempted
                    print("Alternative plan generated, but requires script converter for execution")
                    print(f"Alternative plan: {alternative_plan}")

                except Exception as e:
                    print(f"Error executing alternative plan: {e}")

            return False, f"Execution failed: {message}"

        # Capture final state with retry logic
        try:
            success, final_graph = self._retry_with_backoff(
                self.comm.environment_graph,
                max_retries=3,
                initial_wait=2
            )
            if not success:
                print("Failed to capture final state")
                return False, "Cannot capture final state"
        except Exception as e:
            print(f"Error capturing final state after retries: {e}")
            return False, f"Cannot capture final state: {str(e)}"

        # Verify completion based on task
        verification_result = self._verify_task_completion(task, initial_graph, final_graph)

        print(f"Execution completed")
        print(f"Verification: {verification_result}")

        return execution_success, verification_result

    def _validate_spatial_constraints(self, vh_script):
        """
        Pre-execution spatial validation to catch navigation issues.

        Args:
            vh_script: List of VirtualHome script commands

        Returns:
            bool: Always True (continues execution with warnings)
        """
        print("\n=== SPATIAL VALIDATION ===")

        # Get current scene state
        success, graph = self.comm.environment_graph()
        if not success:
            print("Could not get scene graph for validation")
            return True  # Continue anyway

        # Check if agent can reach target rooms/objects
        issues = []
        for i, action_line in enumerate(vh_script):
            action_parts = action_line.split()
            if len(action_parts) >= 2:
                action = action_parts[1].replace('[', '').replace(']', '')

                if action == 'WALK':
                    # Extract target room/object
                    target = action_parts[2].replace('<', '').replace('>', '')
                    print(f"  Checking walk to: {target}")
                    # For now, just warn about known problematic navigation
                    if target.lower() in ['livingroom']:
                        issues.append(f"Action {i+1}: Navigation to {target} may have collision issues")

        if issues:
            print("Potential spatial issues detected:")
            for issue in issues:
                print(f"    - {issue}")
            print("Proceeding with execution (spatial issues are VirtualHome constraints)")
        else:
            print("No obvious spatial constraint violations detected")

        return True  # Always proceed for now

    def _verify_task_completion(self, task, initial_graph, final_graph):
        """
        Verify task completion by comparing states.

        Args:
            task: Task dictionary
            initial_graph: Initial scene graph
            final_graph: Final scene graph

        Returns:
            str: Verification result message
        """
        task_lower = task['description'].lower()

        # Get state changes
        initial_states = self._extract_object_states(initial_graph)
        final_states = self._extract_object_states(final_graph)

        changes = []
        for obj_id, final_state in final_states.items():
            initial_state = initial_states.get(obj_id, {})
            if final_state != initial_state:
                changes.append(f"Object {obj_id} changed: {initial_state} -> {final_state}")

        # Task-specific verification
        if 'email' in task_lower or 'computer' in task_lower:
            # Check if computer is on
            computer_on = False
            for obj_id, state in final_states.items():
                if any(comp in state.get('class_name', '').lower() for comp in ['computer', 'cpuscreen']):
                    print(f"Computer object {state.get('class_name')}: {state.get('states', [])}")
                    if 'ON' in state.get('states', []):
                        computer_on = True
                        break

            if computer_on:
                return f"SUCCESS: Computer turned on. Changes: {len(changes)}"
            else:
                return f"PARTIAL: Computer not detected as ON. Changes: {len(changes)}"

        elif 'fridge' in task_lower:
            # Check fridge state
            for obj_id, state in final_states.items():
                if 'fridge' in state.get('class_name', '').lower():
                    if 'CLOSED' in state.get('states', []):
                        return f"SUCCESS: Fridge properly closed. Changes: {len(changes)}"
            return f"PARTIAL: Fridge state unclear. Changes: {len(changes)}"

        else:
            # Generic verification
            if len(changes) > 0:
                return f"SUCCESS: Environment changed. Changes: {len(changes)}"
            else:
                return f"UNCLEAR: No significant changes detected"

    def _extract_object_states(self, graph):
        """
        Extract object states from scene graph.

        Args:
            graph: Scene graph dictionary

        Returns:
            dict: Mapping of object IDs to their states
        """
        states = {}
        for node in graph['nodes']:
            states[node['id']] = {
                'class_name': node['class_name'],
                'states': node.get('states', [])
            }
        return states

    def _analyze_failure_and_replan(self, error_message, original_script, task):
        """
        Analyze execution failure and generate alternative plan.

        Args:
            error_message: Error message from execution
            original_script: Original script that failed
            task: Task dictionary

        Returns:
            str: Alternative PDDL plan or None
        """
        print("\nADAPTIVE REPLANNING - Analyzing failure...")

        # Analyze the type of failure
        failure_type = None
        problematic_object = None

        if "Unknown object" in error_message:
            failure_type = "unknown_object"
            # Extract object name from error
            parts = error_message.split("Unknown object")
            if len(parts) > 1:
                problematic_object = parts[1].strip()
        elif "Can not select object" in error_message:
            failure_type = "unreachable_object"
            # Extract object name
            if "REASON:" in error_message:
                parts = error_message.split("Can not select object:")
                if len(parts) > 1:
                    obj_part = parts[1].split(".")[0].strip()
                    problematic_object = obj_part
        elif "collision" in error_message.lower():
            failure_type = "navigation_collision"

        print(f"  Failure type: {failure_type}")
        if problematic_object:
            print(f"  Problematic object: {problematic_object}")

        # Generate alternative strategy based on failure type
        if failure_type == "unknown_object" and problematic_object:
            return self._replan_for_missing_object(problematic_object, task)
        elif failure_type == "unreachable_object":
            return self._replan_for_unreachable_object(problematic_object, task)
        elif failure_type == "navigation_collision":
            return self._replan_for_navigation_collision(task)

        print("  No alternative strategy available for this failure type")
        return None

    def _replan_for_missing_object(self, missing_obj, task):
        """
        Generate alternative plan when object doesn't exist.

        Args:
            missing_obj: Name of missing object
            task: Task dictionary

        Returns:
            str: Alternative PDDL plan or None
        """
        print(f"  Strategy: Find alternative to missing '{missing_obj}'")

        # Create simplified PDDL problem without the missing object
        simplified_prompt = f"""
        The original plan failed because object '{missing_obj}' doesn't exist in the scene.

        Task: {task['description']}

        Generate a SIMPLER plan that accomplishes the core task goal without requiring '{missing_obj}'.
        Focus on the essential actions only.

        Return only a PDDL plan in this format:
        (:plan
          (action1 agent ...)
          (action2 agent ...)
        )
        """

        try:
            response = self.model.generate_content(simplified_prompt)
            alternative_plan = response.text.strip()
            print(f"  Alternative plan generated: {alternative_plan}")
            return alternative_plan
        except Exception as e:
            print(f"  Failed to generate alternative plan: {e}")
            return None

    def _replan_for_unreachable_object(self, unreachable_obj, task):
        """
        Generate plan avoiding unreachable objects.

        Args:
            unreachable_obj: Name of unreachable object
            task: Task dictionary

        Returns:
            str: Alternative PDDL plan or None
        """
        print(f"  Strategy: Avoid unreachable object '{unreachable_obj}'")

        prompt = f"""
        The plan failed because '{unreachable_obj}' cannot be reached by the agent.

        Task: {task['description']}

        Generate an alternative plan that accomplishes the task WITHOUT requiring direct interaction with '{unreachable_obj}'.
        Focus on actions the agent can perform from accessible locations.

        Return only a PDDL plan:
        (:plan
          (action1 agent ...)
        )
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Failed to generate alternative plan: {e}")
            return None

    def _replan_for_navigation_collision(self, task):
        """
        Generate plan avoiding navigation collisions.

        Args:
            task: Task dictionary

        Returns:
            str: Alternative PDDL plan or None
        """
        print("  Strategy: Simplify navigation to avoid collisions")

        prompt = f"""
        The plan failed due to navigation collision issues.

        Task: {task['description']}

        Generate a MINIMAL plan that accomplishes the core task with the simplest possible navigation.
        Prefer actions that don't require complex movement.

        Return only a PDDL plan:
        (:plan
          (action1 agent ...)
        )
        """

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"  Failed to generate alternative plan: {e}")
            return None
