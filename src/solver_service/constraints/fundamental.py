from src.solver_service.components.modeler import Modeler
from src.solver_service.protos import problem_definition_pb2 as problem_pb

# Implements non-negotiable rules that define a valid timetable. A violation of these means the
# timetable is broken.
#
# Constraints Implemented:
# - Teacher Conflict
# - Student Group Conflict
# - Teacher Unavailability
# - System-Wide Breaks (Holidays)


def apply_fundamental_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies all non-negotiable hard constraints like resource conflicts and breaks.

    This function serves as a dispatcher, calling specific subroutines for each
    fundamental constraint.

    Args:
        modeler: The constraint programming modeler instance.
        problem: The problem definition containing all scheduling data.
    """
    _validate_constraints(problem)
    _apply_teacher_conflicts(modeler)
    _apply_student_group_conflicts(modeler)
    _apply_teacher_unavailability(modeler, problem)
    _apply_system_breaks(modeler, problem)


def _validate_constraints(problem: problem_pb.ProblemDefinition) -> None:
    """
    Validates constraint parameters to prevent trivially infeasible problems.

    Args:
        problem: The problem definition containing workload constraints.

    Raises:
        ValueError: If a workload constraint is logically impossible (e.g., max hours
                    per day exceeds available slots).
    """
    slots_per_day = problem.time_grid.slots_per_day
    for constraint in problem.workload_constraints:
        if constraint.max_hours_per_day > slots_per_day:
            raise ValueError(
                f"Teacher {constraint.teacher_id}: max_hours_per_day ({constraint.max_hours_per_day}) "
                f"exceeds slots_per_day ({slots_per_day})."
            )


def _apply_teacher_conflicts(modeler: Modeler) -> None:
    """
    Ensures a teacher is not assigned to more than one activity at the same time.

    Args:
        modeler: The modeler instance containing teacher-to-activity mappings.
    """
    for intervals in modeler.teacher_activity_map.values():
        if len(intervals) > 1:
            modeler.model.AddNoOverlap(intervals)


def _apply_student_group_conflicts(modeler: Modeler) -> None:
    """
    Ensures a student group is not assigned to more than one activity at the same time.

    Args:
        modeler: The modeler instance containing group-to-activity mappings.
    """
    for intervals in modeler.group_activity_map.values():
        if len(intervals) > 1:
            modeler.model.AddNoOverlap(intervals)


def _apply_teacher_unavailability(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Prevents teachers from being scheduled during their pre-defined unavailable slots.

    It creates fixed, 1-slot intervals for each unavailable slot and adds them to a
    NoOverlap constraint along with the teacher's actual activity intervals.

    Args:
        modeler: The modeler instance containing teacher-to-activity mappings.
        problem: The problem definition containing teacher unavailability data.
    """
    slots_per_day = problem.time_grid.slots_per_day
    for teacher in problem.teachers:
        if not teacher.unavailable_slots:
            continue

        teacher_intervals = modeler.teacher_activity_map.get(teacher.id, [])
        if not teacher_intervals:
            continue

        all_intervals_for_teacher = teacher_intervals[:]
        for slot in teacher.unavailable_slots:
            start = slot.day_index * slots_per_day + slot.slot_index
            forbidden_interval = modeler.model.NewFixedSizeIntervalVar(
                start=start,
                size=1,
                name=f"forbidden_{teacher.id}_{slot.day_index}_{slot.slot_index}"
            )
            all_intervals_for_teacher.append(forbidden_interval)
        
        if len(all_intervals_for_teacher) > 1:
            modeler.model.AddNoOverlap(all_intervals_for_teacher)


def _apply_system_breaks(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies system-wide breaks (holidays) where no activities can be scheduled.

    It creates fixed intervals for each break period and ensures no activity interval
    overlaps with any of them.

    Args:
        modeler: The modeler instance containing all activity intervals.
        problem: The problem definition containing system break data.
    """
    slots_per_day = problem.time_grid.slots_per_day
    break_intervals = []
    for break_period in problem.system_breaks:
        start = break_period.start_day * slots_per_day
        duration = (break_period.end_day - break_period.start_day + 1) * slots_per_day
        break_intervals.append(
            modeler.model.NewFixedSizeIntervalVar(start, duration, f"break_{break_period.id}")
        )

    if not break_intervals:
        return

    for activity_interval in modeler.activity_intervals.values():
        modeler.model.AddNoOverlap(break_intervals + [activity_interval])
