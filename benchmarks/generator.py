import random
from solver_service.protos import problem_definition_pb2 as problem_pb

def generate_problem(config: dict) -> problem_pb.ProblemDefinition:
    """
    Generates a realistic, non-trivial ProblemDefinition based on a configuration.

    Args:
        config: A dictionary specifying the problem size and complexity.

    Returns:
        A ProblemDefinition protobuf object.
    """
    problem = problem_pb.ProblemDefinition()
    problem.job_id = f"benchmark-{config['name']}"

    # --- Basic Setup ---
    problem.config.max_solve_time_seconds = 300.0  # 5 minutes
    problem.time_grid.days = 5
    problem.time_grid.slots_per_day = 8

    # --- Generate Entities ---
    teachers = [problem.teachers.add(id=f"T{i+1}", name=f"Teacher_{i+1}") for i in range(config["num_teachers"])]
    groups = [problem.student_groups.add(id=f"G{i+1}", name=f"Group_{i+1}") for i in range(config["num_groups"])]

    # --- Generate Activities ---
    activities = []
    for i in range(config["num_activities"]):
        activity = problem.activities.add(
            id=f"A{i+1}",
            name=f"Activity_{i+1}",
            teacher_id=f"T{(i % config['num_teachers']) + 1}",
            duration_in_slots=random.choice([1, 2])
        )
        assigned_group = groups[i % config["num_groups"]]
        activity.student_group_ids.append(assigned_group.id)
        activities.append(activity)

    # --- Generate Constraints to add difficulty ---
    
    # Teacher Unavailability
    num_teachers_with_unavailability = int(config["num_teachers"] * config["unavail_percent"])
    teachers_to_constrain = random.sample(teachers, num_teachers_with_unavailability)
    for teacher in teachers_to_constrain:
        for _ in range(random.randint(2, 4)): # Each gets 2-4 unavailable slots
            slot = teacher.unavailable_slots.add()
            slot.day_index = random.randint(0, problem.time_grid.days - 1)
            slot.slot_index = random.randint(0, problem.time_grid.slots_per_day - 1)

    # Locked Activities
    num_activities_to_lock = int(config["num_activities"] * config["lock_percent"])
    activities_to_lock = random.sample(activities, num_activities_to_lock)
    for activity in activities_to_lock:
        activity.is_locked = True
        activity.locked_start_time.day_index = random.randint(0, problem.time_grid.days - 1)
        activity.locked_start_time.slot_index = random.randint(0, problem.time_grid.slots_per_day - 2) # Ensure it fits

    # Workload Constraints
    for teacher in teachers:
        workload = problem.workload_constraints.add()
        workload.teacher_id = teacher.id
        workload.max_hours_per_day = 6  # A tight but feasible schedule
        workload.max_gaps_per_day = 2
        workload.penalty_per_gap = 10

    return problem
