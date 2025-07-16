import collections
import numpy as np

from src.solver_service.protos import problem_definition_pb2 as problem_pb
from src.solver_service.protos import solution_pb2 as solution_pb


def analyze_solution(solution: solution_pb.Solution, problem: problem_pb.ProblemDefinition) -> dict:
    """
    Performs a "Solution Autopsy" to calculate tangible quality metrics.

    Args:
        solution: The solution returned by the solver.
        problem: The original problem definition.

    Returns:
        A dictionary of calculated quality metrics.
    """
    if not solution.scheduled_activities:
        return {}

    # --- Data Preparation ---
    activity_map = {act.id: act for act in problem.activities}
    teacher_schedules = collections.defaultdict(lambda: collections.defaultdict(list))

    for sched_act in solution.scheduled_activities:
        activity = activity_map.get(sched_act.activity_id)
        if not activity:
            continue

        teacher_id = activity.teacher_id
        day = sched_act.start_time.day_index
        start_slot = sched_act.start_time.slot_index
        end_slot = start_slot + activity.duration_in_slots

        for slot in range(start_slot, end_slot):
            teacher_schedules[teacher_id][day].append(slot)

    # --- Metric Calculation ---
    workload_std_dev = _calculate_workload_balance(teacher_schedules, activity_map)
    avg_gaps = _calculate_schedule_compactness(teacher_schedules, problem.time_grid.slots_per_day)

    return {
        "workload_std_dev": workload_std_dev,
        "avg_gaps": avg_gaps,
    }


def _calculate_workload_balance(teacher_schedules: dict, activity_map: dict) -> float:
    """Calculates the standard deviation of total hours worked by each teacher."""
    teacher_workloads = collections.defaultdict(int)
    for teacher_id, schedule_by_day in teacher_schedules.items():
        total_hours = sum(len(slots) for slots in schedule_by_day.values())
        teacher_workloads[teacher_id] = total_hours

    if not teacher_workloads:
        return 0.0

    workloads = list(teacher_workloads.values())
    return np.std(workloads)


def _calculate_schedule_compactness(teacher_schedules: dict, slots_per_day: int) -> float:
    """Calculates the average number of gaps in a teacher's daily schedule."""
    total_gaps = 0
    total_teacher_days = 0

    for teacher_id, schedule_by_day in teacher_schedules.items():
        for day, slots in schedule_by_day.items():
            if not slots:
                continue

            total_teacher_days += 1
            min_slot = min(slots)
            max_slot = max(slots)
            
            # The number of slots in the working block
            working_block_span = (max_slot - min_slot) + 1
            # The number of actual worked hours
            worked_hours = len(slots)
            
            gaps = working_block_span - worked_hours
            total_gaps += gaps

    if total_teacher_days == 0:
        return 0.0

    return total_gaps / total_teacher_days
