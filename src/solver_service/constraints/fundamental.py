from src.solver_service.components.constraint_builder import ConstraintBuilder
from src.solver_service.protos import problem_definition_pb2 as problem_pb

# Implements non-negotiable rules that define a valid timetable.


def apply_fundamental_constraints(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """
    Applies all non-negotiable hard constraints like resource conflicts and breaks.
    """
    _apply_resource_conflicts(builder, problem)
    _apply_teacher_unavailability(builder, problem)
    builder.enforce_system_breaks()


def _apply_resource_conflicts(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Ensures teachers and student groups are not double-booked."""
    for teacher in problem.teachers:
        builder.enforce_teacher_conflict(teacher.id)
    for group in problem.student_groups:
        builder.enforce_student_group_conflict(group.id)


def _apply_teacher_unavailability(builder: ConstraintBuilder, problem: problem_pb.ProblemDefinition) -> None:
    """Applies all teacher-specific unavailability constraints."""
    for teacher in problem.teachers:
        builder.enforce_teacher_unavailability(teacher.id)
