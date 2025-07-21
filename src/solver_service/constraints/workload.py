from src.solver_service.components.constraint_builder import ConstraintBuilder
from src.solver_service.protos import problem_definition_pb2 as problem_pb


def apply_all_workload_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies all teacher-specific workload constraints."""
    _apply_basic_workload_constraints(builder, problem)
    _apply_advanced_workload_constraints(builder, problem)


def _apply_basic_workload_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies daily workload constraints from the `WorkloadConstraint` message."""
    for constraint in problem.workload_constraints:
        teacher_intervals = builder._modeler.teacher_activity_map.get(constraint.teacher_id, [])
        if not teacher_intervals:
            continue

        if constraint.max_hours_per_day > 0:
            builder.enforce_max_hours_per_day(constraint.teacher_id, constraint.max_hours_per_day)

        if constraint.penalty_per_gap > 0 and constraint.max_gaps_per_day >= 0:
            builder.penalize_daily_gaps(
                entity_id=f"teacher_{constraint.teacher_id}",
                intervals=teacher_intervals,
                max_gaps=constraint.max_gaps_per_day,
                penalty=constraint.penalty_per_gap
            )


def _apply_advanced_workload_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies weekly workload constraints from the `AdvancedWorkloadConstraint` message."""
    for constraint in problem.advanced_workload_constraints:
        if constraint.max_hours_per_week > 0:
            builder.enforce_max_hours_per_week(constraint.teacher_id, constraint.max_hours_per_week)

        if constraint.max_days_per_week > 0:
            builder.enforce_max_days_per_week(constraint.teacher_id, constraint.max_days_per_week)
