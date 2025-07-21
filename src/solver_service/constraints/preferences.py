from src.solver_service.components.constraint_builder import ConstraintBuilder
from src.solver_service.protos import problem_definition_pb2 as problem_pb


def apply_preference_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies soft preference constraints that affect the quality score."""
    _apply_time_slot_preferences(builder, problem)
    _apply_student_group_gap_penalties(builder, problem)


def _apply_time_slot_preferences(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Adds penalties for scheduling activities outside preferred time slots."""
    pref_map = {p.id: p for p in problem.time_preferences}
    for activity in problem.activities:
        if activity.time_preference_id in pref_map:
            preference = pref_map[activity.time_preference_id]
            builder.penalize_if_not_in_preferred_slots(
                activity.id,
                list(preference.preferred_slots),
                preference.penalty_per_violation
            )


def _apply_student_group_gap_penalties(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies penalties for gaps in student group schedules."""
    if problem.student_gap_penalty_per_day <= 0:
        return

    # This constraint uses the same logic as teacher gap penalties
    for group_id, intervals in builder._modeler.group_activity_map.items():
        builder.penalize_daily_gaps(
            entity_id=f"group_{group_id}",
            intervals=intervals,
            max_gaps=0, # Student schedules should be compact
            penalty=problem.student_gap_penalty_per_day
        )
