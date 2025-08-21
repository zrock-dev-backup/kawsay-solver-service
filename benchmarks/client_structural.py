import grpc
import collections

from src.solver_service.protos import problem_definition_pb2 as problem_pb
from src.solver_service.protos import solution_pb2 as solution_pb
from src.solver_service.protos import solution_pb2_grpc


def create_structural_problem() -> problem_pb.ProblemDefinition:
    """
    Creates a problem focused on structural and preference constraints:
    - Activity Ordering (A before B)
    - Consecutive Activities (C then D)
    - Minimum days between (E and F)
    - Time Slot preference (soft)
    """
    problem = problem_pb.ProblemDefinition()
    problem.job_id = "structural-test-001"

    problem.config.max_solve_time_seconds = 10.0
    problem.time_grid.days = 3
    problem.time_grid.slots_per_day = 4

    # Entities
    problem.teachers.add(id="T1", name="Dr. Turing")
    problem.student_groups.add(id="G1", name="PhD Candidates")

    # Activities
    problem.activities.add(id="A1", name="Research", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A2", name="Publishing", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A3", name="Lecture", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=2)
    problem.activities.add(id="A4", name="Lab", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A5", name="Review", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)

    # Constraint: Research (A1) must happen anytime before Publishing (A2).
    ordering = problem.activity_orderings.add()
    ordering.before_activity_id = "A1"
    ordering.after_activity_id = "A2"

    # Constraint: Lecture (A3) must be immediately followed by Lab (A4).
    consecutive = problem.consecutive_activities.add()
    consecutive.first_activity_id = "A3"
    consecutive.second_activity_id = "A4"

    # Constraint: At least 1 full day must pass between Publishing(A2) and Review(A5).
    min_days = problem.min_days_between_activities.add()
    min_days.first_activity_id = "A2"
    min_days.second_activity_id = "A5"
    min_days.minimum_days = 2  # abs(day(A2)-day(A5)) >= 2

    # Constraint: Prefer to have Review (A5) in the morning (slot 0).
    # This is a soft constraint.
    pref = problem.time_preferences.add()
    pref.id = "morning-reviews"
    pref.preferred_slots.append(0)  # Day 0, Slot 0
    pref.preferred_slots.append(4)  # Day 1, Slot 0
    pref.preferred_slots.append(8)  # Day 2, Slot 0
    pref.penalty_per_violation = 50

    review_activity = next(a for a in problem.activities if a.id == "A5")
    review_activity.time_preference_id = "morning-reviews"

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
        for i in range(activity.duration_in_slots): grid[
            (start_day, start_slot + i)] = f"{activity.name[:10]} ({activity.id})"
    header = f"{'Time':<10}"
    [header := header + f"| {'Day ' + str(day):<20} " for day in range(problem.time_grid.days)]
    print(header)
    print("-" * len(header))
    for slot in range(slots_per_day):
        row = f"{'Slot ' + str(slot):<10}";
        [row := row + f"| {grid[(day, slot)]:<20} " for day in range(problem.time_grid.days)]
        print(row)


def run(problem_factory):
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = solution_pb2_grpc.TimetablingServiceStub(channel)
        problem = problem_factory()
        print(f"--- Sending Problem '{problem.job_id}' to Server ---")
        response = stub.Solve(problem)
        print_solution(response, problem)


if __name__ == "__main__":
    run(create_structural_problem)
