import grpc
import collections

from src.solver_service.protos import problem_definition_pb2 as problem_pb
from src.solver_service.protos import solution_pb2 as solution_pb
from src.solver_service.protos import solution_pb2_grpc

def create_workload_problem() -> problem_pb.ProblemDefinition:
    """
    Creates a problem focused on workload constraints:
    - max_hours_per_day (hard)
    - max_days_per_week (hard)
    - max_gaps_per_day (soft)
    """
    problem = problem_pb.ProblemDefinition()
    problem.job_id = "workload-test-001"

    problem.config.max_solve_time_seconds = 10.0
    problem.time_grid.days = 5
    problem.time_grid.slots_per_day = 4

    # Entities
    problem.teachers.add(id="T1", name="Dr. Turing")
    problem.student_groups.add(id="G1", name="Post-Grads")

    # Dr. Turing has 4 one-hour activities.
    problem.activities.add(id="A1", name="Thesis 1", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A2", name="Thesis 2", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A3", name="Thesis 3", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A4", name="Thesis 4", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)

    # Constraint: Dr. Turing can work max 2 hours per day.
    # This forces his 4 hours of work to be spread over at least 2 days.
    workload = problem.workload_constraints.add()
    workload.teacher_id = "T1"
    workload.max_hours_per_day = 2
    workload.max_gaps_per_day = 0 # Penalize any gaps between classes on the same day
    workload.penalty_per_gap = 25 # High penalty to ensure compact schedule

    # Constraint: Dr. Turing can work max 2 days per week.
    # Combined with the above, this creates a tight fit: 2 days of 2 hours each.
    adv_workload = problem.advanced_workload_constraints.add()
    adv_workload.teacher_id = "T1"
    adv_workload.max_days_per_week = 2

    return problem

# (Re-use print_solution and run functions from client_fundamental.py)
def print_solution(solution: solution_pb.Solution, problem: problem_pb.ProblemDefinition):
    print("\n--- Solution Received from Server ---")
    print(f"Job ID: {solution.job_id}")
    print(f"Status: {solution_pb.SolverStatus.Name(solution.status)}")
    print(f"Message: {solution.message}")
    if solution.status in [solution_pb.OPTIMAL, solution_pb.FEASIBLE]:
        print(f"Objective Value (Quality Score): {solution.quality_score}")
    if solution.status not in [solution_pb.OPTIMAL, solution_pb.FEASIBLE]: return
    activity_map = {act.id: act for act in problem.activities}
    slots_per_day = problem.time_grid.slots_per_day
    grid = collections.defaultdict(str)
    for sched_act in solution.scheduled_activities:
        activity = activity_map.get(sched_act.activity_id)
        if not activity: continue
        start_day, start_slot = sched_act.start_time.day_index, sched_act.start_time.slot_index
        for i in range(activity.duration_in_slots): grid[(start_day, start_slot + i)] = f"{activity.name[:10]} ({activity.teacher_id})"
    header = f"{'Time':<10}"
    [header := header + f"| {'Day ' + str(day):<20} "
     for day in range(problem.time_grid.days)]
    print(header)
    print("-" * len(header))
    for slot in range(slots_per_day):
        row = f"{'Slot ' + str(slot):<10}"; [row := row + f"| {grid[(day, slot)]:<20} " for day in range(problem.time_grid.days)]; print(row)

def run(problem_factory):
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = solution_pb2_grpc.TimetablingServiceStub(channel)
        problem = problem_factory()
        print(f"--- Sending Problem '{problem.job_id}' to Server ---")
        response = stub.Solve(problem)
        print_solution(response, problem)

if __name__ == "__main__":
    run(create_workload_problem)