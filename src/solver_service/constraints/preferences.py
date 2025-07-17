from src.solver_service.components.modeler import Modeler
from src.solver_service.protos import problem_definition_pb2 as problem_pb
from . import utils

# Implements soft constraints used to guide the solver towards a "better" solution.
# These are the primary inputs for the objective function (quality score).
#
# Constraints Implemented:
# - Preferred Time Slots (for activities)
# - Student Group Gap Penalties


def apply_preference_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies soft preference constraints that affect the quality score.

    Args:
        modeler: The constraint programming modeler instance.
        problem: The problem definition containing preference data.
    """
    _apply_time_slot_preferences(modeler, problem)
    _apply_student_group_gap_penalties(modeler, problem)


def _apply_time_slot_preferences(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Adds penalties for scheduling activities outside of preferred time slots.

    For each activity with an associated time preference, this function adds a term to
    the objective function that is activated if the activity is scheduled outside of
    the allowed set of start times.

    Args:
        modeler: The modeler instance containing activity intervals and objective penalties.
        problem: The problem definition containing time preference data.
    """
    pref_map = {p.id: p for p in problem.time_preferences}

    for activity_id, interval in modeler.activity_intervals.items():
        activity = modeler.id_to_activity_map[activity_id]
        preference_id = activity.time_preference_id

        if not preference_id or preference_id not in pref_map:
            continue

        preference = pref_map[preference_id]
        preferred_slots = set(preference.preferred_slots)
        if not preferred_slots:
            continue

        is_not_preferred = modeler.model.NewBoolVar(f"not_preferred_{activity_id}")
        modeler.model.Add(interval.StartExpr().NotMember(list(preferred_slots))).OnlyEnforceIf(is_not_preferred)

        modeler.objective_penalties.append(is_not_preferred * preference.penalty_per_violation)


def _apply_student_group_gap_penalties(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies penalties for gaps in student group schedules to create compact schedules.

    This function uses utility helpers to count the number of idle slots between the
    first and last activity of a day for a student group and adds a proportional
    penalty to the objective function.

    Args:
        modeler: The modeler instance.
        problem: The problem definition containing student gap penalty info.
    """
    if not problem.student_gap_penalty_per_day > 0:
        return

    slots_per_day = problem.time_grid.slots_per_day
    for group_id, intervals in modeler.group_activity_map.items():
        if len(intervals) <= 1:
            continue

        for day in range(problem.time_grid.days):
            is_working = utils.create_working_status_variables(
                modeler.model, f"group_{group_id}", intervals, day, slots_per_day
            )
            num_gaps = utils.count_gaps_in_schedule(
                modeler.model, f"group_{group_id}", day, is_working
            )
            modeler.objective_penalties.append(num_gaps * problem.student_gap_penalty_per_day)
