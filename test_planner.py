from unified_planning.shortcuts import *
from unified_planning.io import PDDLReader
from unified_planning.engines import PlanGenerationResultStatus


def run_unified_planner(domain_file, problem_file):
    reader = PDDLReader()
    problem = reader.parse_problem(domain_file, problem_file)

    with OneshotPlanner(name="pyperplan") as planner:
        result = planner.solve(problem)

        if result.status == PlanGenerationResultStatus.SOLVED_SATISFICING:
            print("Planner finished. Plan found.")
            return [str(action) for action in result.plan.actions]
        else:
            print("Planner failed. Status:", result.status)
            return []

def main():
    plan = run_unified_planner(r"C:\Users\talsc\PycharmProjects\virtualhome_llm_project\core\pddl_system\virtualhome_pddl_domain.pddl",
                      r"C:\Users\talsc\PycharmProjects\virtualhome_llm_project\core\pddl_system\tasks\vh_task_1_Put groceries in Fridge.pddl")

    for step in plan:
        print(step)


if __name__ == '__main__':
    main()