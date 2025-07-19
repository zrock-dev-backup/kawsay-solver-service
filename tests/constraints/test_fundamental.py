import pytest
from ortools.sat.python import cp_model

from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints import fundamental
from .. import conftest


# This test does not use the solver, it validates input logic. It can remain.
def test_validate_constraints_raises_error_on_invalid_input():
    """Verifies that validation catches impossible constraint values."""
    problem = conftest.create_problem(days=1, slots_per_day=8)
    constraint = problem.workload_constraints.add()
    constraint.teacher_id = "T1"
    constraint.max_hours_per_day = 9  # Impossible

    with pytest.raises(ValueError, match="exceeds slots_per_day"):
        fundamental._validate_constraints(problem)


def test_teacher_conflicts_are_infeasible(solve_model):
    """A teacher cannot teach two classes at once."""
    problem = conftest.create_problem(days=1, slots_per_day=2)
    problem.teachers.add(id="T1")
    problem.activities.add(id="A1", teacher_id="T1", duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})
    problem.activities.add(id="A2", teacher_id="T1", duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})

    modeler = Modeler(problem)
    fundamental._apply_teacher_conflicts(modeler)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_student_group_conflicts_are_infeasible(solve_model):
    """A student group cannot attend two classes at once."""
    problem = conftest.create_problem(days=1, slots_per_day=2)
    problem.student_groups.add(id="G1")
    problem.activities.add(id="A1", student_group_ids=["G1"], duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})
    problem.activities.add(id="A2", student_group_ids=["G1"], duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})

    modeler = Modeler(problem)
    fundamental._apply_student_group_conflicts(modeler)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_teacher_unavailability_is_enforced(solve_model):
    """An activity cannot be scheduled in a teacher's unavailable slot."""
    problem = conftest.create_problem(days=1, slots_per_day=1)
    teacher = problem.teachers.add(id="T1")
    teacher.unavailable_slots.add(day_index=0, slot_index=0)
    problem.activities.add(id="A1", teacher_id="T1", duration_in_slots=1) # Must go in the only slot

    modeler = Modeler(problem)
    fundamental._apply_teacher_unavailability(modeler, problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_system_breaks_are_enforced(solve_model):
    """An activity cannot be scheduled during a system-wide break."""
    problem = conftest.create_problem(days=1, slots_per_day=1)
    problem.system_breaks.add(id="holiday", start_day=0, end_day=0)
    problem.activities.add(id="A1", duration_in_slots=1) # Must go in the only slot

    modeler = Modeler(problem)
    fundamental._apply_system_breaks(modeler, problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE
