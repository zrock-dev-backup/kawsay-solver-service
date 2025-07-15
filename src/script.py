import collections
from ortools.sat.python import cp_model

import problem_definition_pb2 as problem_pb
import solution_pb2 as solution_pb

def solve_timetable(problem: problem_pb.ProblemDefinition) -> solution_pb.Solution:
    """
    Builds and solves a timetabling model from a ProblemDefinition.
    """
    print("--- Starting Timetable Solve ---")
    
    # 1. Create the CP-SAT Model
    model = cp_model.CpModel()

    # 2. Create the Decision Variables
    # string IDs to the OR-Tools variables map.
    activity_intervals = {}
    
    # The domain for our time variables is a single integer representing the start slot
    # from the beginning of the week. E.g., Day 0, Slot 0 -> 0. Day 1, Slot 0 -> slots_per_day.
    slots_per_day = problem.time_grid.slots_per_day
    total_slots = problem.time_grid.days * slots_per_day
    domain = (0, total_slots - 1)

    print(f"Time Grid: {problem.time_grid.days} days, {slots_per_day} slots/day. Total slots: {total_slots}")

    for activity in problem.activities:
        # Create the start time variable for this activity.
        start_var = model.NewIntVar(domain[0], domain[1], f"start_{activity.id}")
        
        # Create the core Interval Variable. This is the central abstraction.
        # It represents a block of time with a start, duration, and end.
        interval_var = model.NewIntervalVar(
            start=start_var,
            size=activity.duration_in_slots,
            end=start_var + activity.duration_in_slots,
            name=f"interval_{activity.id}"
        )
        activity_intervals[activity.id] = interval_var
        
        # Handle locked activities (from User Story 1)
        if activity.is_locked:
            locked_start_slot = activity.locked_start_time.day_index * slots_per_day + activity.locked_start_time.slot_index
            print(f"Activity '{activity.name}' is LOCKED to start at slot {locked_start_slot}")
            model.Add(start_var == locked_start_slot)

    # 3. Add the Hard Constraints

    # Constraint: Teacher Conflict
    # For each teacher, ensure none of their assigned activity intervals overlap.
    teacher_activity_map = collections.defaultdict(list)
    for activity in problem.activities:
        teacher_activity_map[activity.teacher_id].append(activity_intervals[activity.id])

    for teacher_id, intervals in teacher_activity_map.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)
            print(f"Added NoOverlap constraint for Teacher '{teacher_id}'")

    # Constraint: Student Group Conflict
    # For each student group, ensure none of their assigned activity intervals overlap.
    group_activity_map = collections.defaultdict(list)
    for activity in problem.activities:
        for group_id in activity.student_group_ids:
            group_activity_map[group_id].append(activity_intervals[activity.id])

    for group_id, intervals in group_activity_map.items():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)
            print(f"Added NoOverlap constraint for Student Group '{group_id}'")
            
    # Constraint: Teacher Unavailability (from User Story 2)
    for teacher in problem.teachers:
        if not teacher.unavailable_slots:
            continue
        
        print(f"Processing unavailability for Teacher '{teacher.name}'...")
        # Get all activities for this teacher
        teacher_intervals = teacher_activity_map.get(teacher.id, [])
        if not teacher_intervals:
            continue
            
        # For each unavailable slot, forbid all of the teacher's activities from running.
        for slot in teacher.unavailable_slots:
            start_of_forbidden_slot = slot.day_index * slots_per_day + slot.slot_index
            # Create a fixed-size interval of size 1 for the forbidden slot
            forbidden_interval = model.NewIntervalVar(
                start=start_of_forbidden_slot,
                size=1,
                end=start_of_forbidden_slot + 1,
                name=f"forbidden_{teacher.id}_{slot.day_index}_{slot.slot_index}"
            )
            
            # Add a NoOverlap constraint between the forbidden slot and ALL of the teacher's activities.
            # This is a common and effective pattern.
            for activity_interval in teacher_intervals:
                model.AddNoOverlap([activity_interval, forbidden_interval])


    # 4. Create the Solver and Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = problem.config.max_solve_time_seconds
    
    print("\n--- Solving Model ---")
    status = solver.Solve(model)
    print(f"Solver status: {solver.StatusName(status)}")

    # 5. Process the Solution
    solution = solution_pb.Solution()
    solution.job_id = problem.job_id
    solution.status = solution_pb.SolverStatus.Value(solver.StatusName(status))

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        solution.message = "A valid schedule was found."
        for activity in problem.activities:
            start_slot_val = solver.Value(activity_intervals[activity.id].StartExpr())
            
            scheduled_activity = solution.scheduled_activities.add()
            scheduled_activity.activity_id = activity.id
            scheduled_activity.start_time.day_index = start_slot_val // slots_per_day
            scheduled_activity.start_time.slot_index = start_slot_val % slots_per_day
    elif status == cp_model.INFEASIBLE:
        solution.message = "The problem is infeasible. No solution exists under the given constraints."
    else:
        solution.message = "An error occurred during solving."
        
    return solution


def create_mock_problem() -> problem_pb.ProblemDefinition:
    """Creates a hard-coded problem for testing."""
    problem = problem_pb.ProblemDefinition()
    problem.job_id = "spike-job-001"
    
    # Config
    problem.config.max_solve_time_seconds = 30.0
    problem.time_grid.days = 3  # Mon, Tue, Wed
    problem.time_grid.slots_per_day = 4 # 9am, 10am, 11am, 12pm

    # Entities
    problem.teachers.add(id="T1", name="Dr. Turing")
    problem.teachers.add(id="T2", name="Dr. Hopper")
    
    # --- Constraint Test: Dr. Hopper is unavailable on Monday at 10am ---
    hopper = next(t for t in problem.teachers if t.id == "T2")
    unavailable_slot = hopper.unavailable_slots.add()
    unavailable_slot.day_index = 0 # Monday
    unavailable_slot.slot_index = 1 # 10am slot

    problem.student_groups.add(id="G1", name="First Year CS")
    problem.student_groups.add(id="G2", name="Second Year CS")

    # Activities
    problem.activities.add(id="A1", name="Intro to AI", teacher_id="T1", student_group_ids=["G1"], duration_in_slots=2)
    problem.activities.add(id="A2", name="Databases", teacher_id="T2", student_group_ids=["G1"], duration_in_slots=1)
    problem.activities.add(id="A3", name="Algorithms", teacher_id="T1", student_group_ids=["G2"], duration_in_slots=1)
    problem.activities.add(id="A4", name="Compilers", teacher_id="T2", student_group_ids=["G2"], duration_in_slots=1)
    
    # --- Constraint Test: Lock "Algorithms" to Wednesday at 9am ---
    algo_activity = next(a for a in problem.activities if a.id == "A3")
    algo_activity.is_locked = True
    algo_activity.locked_start_time.day_index = 2 # Wednesday
    algo_activity.locked_start_time.slot_index = 0 # 9am slot
    
    return problem

def print_solution(solution: solution_pb.Solution, problem: problem_pb.ProblemDefinition):
    """Prints the solution in a human-readable format."""
    print("\n--- Solution ---")
    print(f"Job ID: {solution.job_id}")
    print(f"Status: {solution_pb.SolverStatus.Name(solution.status)}")
    print(f"Message: {solution.message}")
    
    if solution.status not in [solution_pb.OPTIMAL, solution_pb.FEASIBLE]:
        return
        
    # Create a nice grid for visualization
    slots_per_day = problem.time_grid.slots_per_day
    grid = collections.defaultdict(lambda: "---")
    
    for sched_act in solution.scheduled_activities:
        activity = next(a for a in problem.activities if a.id == sched_act.activity_id)
        start_day = sched_act.start_time.day_index
        start_slot = sched_act.start_time.slot_index
        
        for i in range(activity.duration_in_slots):
            grid[(start_day, start_slot + i)] = f"{activity.name[:12]:<12}"
            
    # Print header
    header = f"{'Time':<10}"
    for day in range(problem.time_grid.days):
        header += f"| {'Day ' + str(day):<12} "
    print(header)
    print("-" * len(header))
    
    # Print rows
    for slot in range(slots_per_day):
        row = f"{'Slot ' + str(slot):<10}"
        for day in range(problem.time_grid.days):
            row += f"| {grid[(day, slot)]:<12} "
        print(row)


if __name__ == "__main__":
    mock_problem = create_mock_problem()
    solution_result = solve_timetable(mock_problem)
    print_solution(solution_result, mock_problem)
