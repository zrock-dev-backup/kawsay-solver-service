import grpc
import collections

from solver_service.protos import problem_definition_pb2 as problem_pb
from solver_service.protos import solution_pb2 as solution_pb
from solver_service.protos import solution_pb2_grpc

def create_mock_problem() -> problem_pb.ProblemDefinition:
    """Creates a hard-coded problem for testing."""
    problem = problem_pb.ProblemDefinition()
    problem.job_id = "client-job-002"
    
    # Config
    problem.config.max_solve_time_seconds = 30.0
    problem.time_grid.days = 3
    problem.time_grid.slots_per_day = 4

    # Entities
    problem.teachers.add(id="T1", name="Dr. Turing")
    problem.teachers.add(id="T2", name="Dr. Hopper")
    
    hopper = next(t for t in problem.teachers if t.id == "T2")
    unavailable_slot = hopper.unavailable_slots.add()
    unavailable_slot.day_index = 0
    unavailable_slot.slot_index = 1

    problem.student_groups.add(id="G1", name="First Year CS")
    problem.student_groups.add(id="G2", name="Second Year CS")

    # Activities
    problem.activities.add(id="A1", name="Intro to AI", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=2)
    problem.activities.add(id="A2", name="Databases", teacher_id="T2", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A3", name="Algorithms", teacher_id="T1", student_group_ids=["G2"], duration_in_slots=1)
    problem.activities.add(id="A4", name="Compilers", teacher_id="T2", student_group_ids=["G2"], duration_in_slots=1)
    
    algo_activity = next(a for a in problem.activities if a.id == "A3")
    algo_activity.is_locked = True
    algo_activity.locked_start_time.day_index = 2
    algo_activity.locked_start_time.slot_index = 0

    # --- Constraint Test: Add workload constraints for Dr. Turing ---
    workload_turing = problem.workload_constraints.add()
    workload_turing.teacher_id = "T1"
    workload_turing.max_gaps_per_day = 1  # Dr. Turing wants a compact schedule
    workload_turing.penalty_per_gap = 10   # Make gaps costly
    workload_turing.max_hours_per_day = 0 # Hard limit of 3 hours per day

    # --- Constraint Test: Add workload constraints for Dr. Hopper ---
    workload_hopper = problem.workload_constraints.add()
    workload_hopper.teacher_id = "T2"
    workload_hopper.max_hours_per_day = 2 # Hard limit of 2 hours per day
    # Dr. Hopper doesn't have a gap constraint, so we don't set it.
    
    return problem

def print_solution(solution: solution_pb.Solution, problem: problem_pb.ProblemDefinition):
    """Prints the solution in a human-readable format."""
    print("\n--- Solution Received from Server ---")
    print(f"Job ID: {solution.job_id}")
    print(f"Status: {solution_pb.SolverStatus.Name(solution.status)}")
    print(f"Message: {solution.message}")
    
    if solution.status not in [solution_pb.OPTIMAL, solution_pb.FEASIBLE]:
        return
        
    slots_per_day = problem.time_grid.slots_per_day
    grid = collections.defaultdict(lambda: "---")
    
    for sched_act in solution.scheduled_activities:
        activity = next(a for a in problem.activities if a.id == sched_act.activity_id)
        start_day = sched_act.start_time.day_index
        start_slot = sched_act.start_time.slot_index
        
        for i in range(activity.duration_in_slots):
            grid[(start_day, start_slot + i)] = f"{activity.name[:12]:<12}"
            
    header = f"{'Time':<10}"
    for day in range(problem.time_grid.days):
        header += f"| {'Day ' + str(day):<12} "
    print(header)
    print("-" * len(header))
    
    for slot in range(slots_per_day):
        row = f"{'Slot ' + str(slot):<10}"
        for day in range(problem.time_grid.days):
            row += f"| {grid[(day, slot)]:<12} "
        print(row)

def run():
    """Runs the test client."""
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = solution_pb2_grpc.TimetablingServiceStub(channel)
        
        mock_problem = create_mock_problem()
        print("--- Sending Problem to Server ---")
        
        response = stub.Solve(mock_problem)
        
        print_solution(response, mock_problem)

if __name__ == "__main__":
    run()
