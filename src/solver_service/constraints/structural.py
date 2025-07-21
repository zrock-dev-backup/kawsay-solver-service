from src.solver_service.components.constraint_builder import ConstraintBuilder
from src.solver_service.protos import problem_definition_pb2 as problem_pb


def apply_all_structural_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies all structural constraints that shape the schedule."""
    _apply_day_boundary_constraints(builder, problem)
    _apply_activity_relation_constraints(builder, problem)


def _apply_day_boundary_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Prevents activities from crossing day boundaries."""
    for activity in problem.activities:
        builder.enforce_day_boundaries(activity.id)


def _apply_activity_relation_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies ordering, consecutiveness, and minimum days between activities."""
    for ordering in problem.activity_orderings:
        builder.enforce_activity_ordering(ordering.before_activity_id, ordering.after_activity_id)

    for consecutive in problem.consecutive_activities:
        builder.enforce_consecutive_activities(consecutive.first_activity_id, consecutive.second_activity_id)

    for min_days in problem.min_days_between_activities:
        builder.enforce_min_days_between(
            min_days.first_activity_id,
            min_days.second_activity_id,
            min_days.minimum_days
        )
