from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader
from unified_planning.engines import PlanGenerationResultStatus


def run_unified_planner(domain_file, problem_file):
    reader = PDDLReader()
    print("domain_file:", domain_file)
    print("problem_file:", problem_file)
    problem = reader.parse_problem(domain_file, problem_file)

    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)

        if result.status == PlanGenerationResultStatus.SOLVED_SATISFICING:
            print("Planner finished. Plan found.")
            return [str(action) for action in result.plan.actions]
        else:
            print("Planner failed. Status:", result.status)
            return []

def run_unified_planner_string(domain_str, problem_str):
    """
    Run Unified Planning with domain and problem provided as strings.
    :param domain_str: PDDL domain as a string
    :param problem_str: PDDL problem as a string
    :return: string of the plan or failure message. separate the lines by \n
    """
    # start by creating temporary files locally in the project directory
    domain_str = domain_str.replace("`", "")
    problem_str = problem_str.replace("`", "")
    print("domain_str:", domain_str)
    print("problem_str:", problem_str)
    # create a directory called temp_pddl_files if it doesn't exist
    import os
    temp_dir = "temp_pddl_files"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    domain_file_path = os.path.join(temp_dir, "temp_domain.pddl")
    problem_file_path = os.path.join(temp_dir, "temp_problem.pddl")
    with open(domain_file_path, 'w') as f:
        f.write(domain_str)
    with open(problem_file_path, 'w') as f:
        f.write(problem_str)

    plan = run_unified_planner(domain_file_path, problem_file_path)
    if not plan:
        raise RuntimeError("Planner failed. No plan found.")
    print("The plan is:")
    for step in plan:
        print(step)
    plan = "\n".join(plan)
    # import os
    # os.remove(domain_file_path)
    # os.remove(problem_file_path)
    return plan

def main():
    plan = run_unified_planner(r"C:\Users\talsc\PycharmProjects\virtualhome_llm_project\core\pddl_system\virtualhome_pddl_domain.pddl",
                      r"C:\Users\talsc\PycharmProjects\virtualhome_llm_project\core\pddl_system\tasks\vh_task_1_Put groceries in Fridge.pddl")

    for step in plan:
        print(step)


if __name__ == '__main__':
    main()