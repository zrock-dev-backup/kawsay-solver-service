import grpc
import collections

from src.solver_service.protos import problem_definition_pb2 as problem_pb
from src.solver_service.protos import solution_pb2 as solution_pb
from src.solver_service.protos import solution_pb2_grpc

def create_fundamental_problem() -> problem_pb.ProblemDefinition:
    """
    Creates a problem focused on fundamental constraints:
    - Teacher/Student conflicts.
    - Teacher unavailability.
    """
    problem = problem_pb.ProblemDefinition()
    problem.job_id = "fundamental-test-001"

    problem.config.max_solve_time_seconds = 10.0
    problem.time_grid.days = 2
    problem.time_grid.slots_per_day = 4

    # Entities
    problem.teachers.add(id="T1", name="Dr. Turing")
    problem.teachers.add(id="T2", name="Dr. Hopper")
    problem.student_groups.add(id="G1", name="First Year CS")

    # Constraint: Dr. Hopper is unavailable on Day 0, Slot 1
    hopper = next(t for t in problem.teachers if t.id == "T2")
    unavailable = hopper.unavailable_slots.add()
    unavailable.day_index = 0
    unavailable.slot_index = 1

    # Activities designed to create conflicts if not handled
    # T1 teaches two classes to G1. They cannot overlap.
    problem.activities.add(id="A1", name="Intro to CS", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=2)
    problem.activities.add(id="A2", name="Logic", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=1)

    # T2 teaches a class that must avoid the unavailable slot.
    problem.activities.add(id="A3", name="Compilers", teacher_id="T2", student_group_ids=["G1"], duration_in_slots=1)

    return problem

def print_solution(solution: solution_pb.Solution, problem: problem_pb.ProblemDefinition):
    """Prints the solution in a human-readable format."""
    print("\n--- Solution Received from Server ---")
    print(f"Job ID: {solution.job_id}")
    print(f"Status: {solution_pb.SolverStatus.Name(solution.status)}")
    print(f"Message: {solution.message}")

    if solution.status not in [solution_pb.OPTIMAL, solution_pb.FEASIBLE]:
        return

    activity_map = {act.id: act for act in problem.activities}
    slots_per_day = problem.time_grid.slots_per_day
    grid = collections.defaultdict(str)

    # Mark unavailable slots
    for teacher in problem.teachers:
        for slot in teacher.unavailable_slots:
            grid[(slot.day_index, slot.slot_index)] = f"UNAVAIL({teacher.id})"

    for sched_act in solution.scheduled_activities:
        activity = activity_map.get(sched_act.activity_id)
        if not activity: continue

        start_day = sched_act.start_time.day_index
        start_slot = sched_act.start_time.slot_index

        for i in range(activity.duration_in_slots):
            grid[(start_day, start_slot + i)] = f"{activity.name[:10]} ({activity.teacher_id})"

    header = f"{'Time':<10}"
    for day in range(problem.time_grid.days):
        header += f"| {'Day ' + str(day):<20} "
    print(header)
    print("-" * len(header))

    for slot in range(slots_per_day):
        row = f"{'Slot ' + str(slot):<10}"
        for day in range(problem.time_grid.days):
            row += f"| {grid[(day, slot)]:<20} "
        print(row)

def run(problem_factory):
    """Runs the test client with a given problem factory."""
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = solution_pb2_grpc.TimetablingServiceStub(channel)

        problem = problem_factory()
        print(f"--- Sending Problem '{problem.job_id}' to Server ---")

        response = stub.Solve(problem)
        print_solution(response, problem)

if __name__ == "__main__":
    run(create_fundamental_problem)