from src.solver_service.components.modeler import Modeler
from src.solver_service.protos import problem_definition_pb2 as problem_pb


# Implements constraints that define the shape and structure of the schedule.
#
# Constraints Implemented:
# - Day Boundary Constraint (no activity crosses a day)
# - Activity Ordering (A before B)
# - Consecutive Activities (A right after B)
# - Minimum Days Between Activities


def apply_all_structural_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies all structural constraints that shape the schedule.

    Args:
        modeler: The constraint programming modeler instance.
        problem: The problem definition containing all scheduling data.
    """
    _apply_day_boundary_constraints(modeler, problem)
    _apply_activity_relation_constraints(modeler, problem)


def _apply_day_boundary_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Prevents activities from crossing day boundaries.

    It enforces that for any given activity, the day index of its start slot is
    the same as the day index of its end slot.

    Args:
        modeler: The modeler instance containing all activity intervals.
        problem: The problem definition containing time grid data.
    """
    slots_per_day = problem.time_grid.slots_per_day
    for activity_id, interval in modeler.activity_intervals.items():
        activity = modeler.id_to_activity_map[activity_id]
        if activity.duration_in_slots > slots_per_day:
            continue

        start_var = interval.StartExpr()
        start_day = modeler.model.NewIntVar(0, problem.time_grid.days - 1, f"start_day_{activity_id}")
        end_day = modeler.model.NewIntVar(0, problem.time_grid.days - 1, f"end_day_{activity_id}")

        modeler.model.AddDivision(target=start_day, expr=start_var, mod=slots_per_day)
        modeler.model.AddDivision(target=end_day, expr=interval.EndExpr() - 1, mod=slots_per_day)
        modeler.model.Add(start_day == end_day)


def _apply_activity_relation_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies ordering, consecutiveness, and minimum days between activities.

    This function serves as a dispatcher for various activity relationship rules.

    Args:
        modeler: The constraint programming modeler instance.
        problem: The problem definition containing activity relation data.
    """
    _apply_activity_ordering(modeler, problem)
    _apply_consecutive_activities(modeler, problem)
    _apply_min_days_between_activities(modeler, problem)


def _apply_activity_ordering(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Ensures a specific activity is scheduled before another.

    Args:
        modeler: The modeler instance containing activity intervals.
        problem: The problem definition containing activity ordering rules.
    """
    for ordering in problem.activity_orderings:
        before_interval = modeler.activity_intervals[ordering.before_activity_id]
        after_interval = modeler.activity_intervals[ordering.after_activity_id]
        modeler.model.Add(before_interval.EndExpr() <= after_interval.StartExpr())


def _apply_consecutive_activities(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Ensures two specific activities are scheduled back-to-back.

    Args:
        modeler: The modeler instance containing activity intervals.
        problem: The problem definition containing consecutive activity rules.
    """
    for consecutive in problem.consecutive_activities:
        first_interval = modeler.activity_intervals[consecutive.first_activity_id]
        second_interval = modeler.activity_intervals[consecutive.second_activity_id]
        modeler.model.Add(first_interval.EndExpr() == second_interval.StartExpr())


def _apply_min_days_between_activities(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Ensures a minimum number of full days pass between two activities.

    Args:
        modeler: The modeler instance containing activity intervals.
        problem: The problem definition containing min-days-between rules.
    """
    slots_per_day = problem.time_grid.slots_per_day
    for min_days in problem.min_days_between_activities:
        first_interval = modeler.activity_intervals[min_days.first_activity_id]
        second_interval = modeler.activity_intervals[min_days.second_activity_id]

        first_day = modeler.model.NewIntVar(0, problem.time_grid.days - 1, f"day_{min_days.first_activity_id}")
        second_day = modeler.model.NewIntVar(0, problem.time_grid.days - 1, f"day_{min_days.second_activity_id}")

        modeler.model.AddDivision(first_day, first_interval.StartExpr(), slots_per_day)
        modeler.model.AddDivision(second_day, second_interval.StartExpr(), slots_per_day)

        modeler.model.AddAbs(second_day - first_day) >= min_days.minimum_days
