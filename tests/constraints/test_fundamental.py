import pytest
from ortools.sat.python import cp_model

from src.solver_service.components.modeler import Modeler
from src.solver_service.handlers.fundamental_handler import FundamentalConstraintHandler

from .. import conftest

def test_teacher_conflicts_are_infeasible(solve_model):
    """A teacher cannot teach two classes at once."""
    problem = conftest.create_problem(days=1, slots_per_day=2)
    problem.teachers.add(id="T1")
    problem.activities.add(
        id="A1",
        teacher_id="T1",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )
    problem.activities.add(
        id="A2",
        teacher_id="T1",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )

    modeler = Modeler(problem)
    handler = FundamentalConstraintHandler(modeler)
    handler._enforce_resource_conflicts(problem) 
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_student_group_conflicts_are_infeasible(solve_model):
    """A student group cannot attend two classes at once."""
    problem = conftest.create_problem(days=1, slots_per_day=2)
    problem.student_groups.add(id="G1")
    problem.activities.add(
        id="A1",
        student_group_ids=["G1"],
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )
    problem.activities.add(
        id="A2",
        student_group_ids=["G1"],
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )

    modeler = Modeler(problem)
    handler = FundamentalConstraintHandler(modeler)
    handler._enforce_resource_conflicts(problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_teacher_unavailability_is_enforced(solve_model):
    """An activity cannot be scheduled in a teacher's unavailable slot."""
    problem = conftest.create_problem(days=1, slots_per_day=1)
    teacher = problem.teachers.add(id="T1")
    teacher.unavailable_slots.add(day_index=0, slot_index=0)
    problem.activities.add(
        id="A1", teacher_id="T1", duration_in_slots=1
    )  # Must go in the only slot

    modeler = Modeler(problem)
    handler = FundamentalConstraintHandler(modeler)
    handler._enforce_teacher_unavailability(problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_system_breaks_are_enforced(solve_model):
    """An activity cannot be scheduled during a system-wide break."""
    problem = conftest.create_problem(days=1, slots_per_day=1)
    problem.system_breaks.add(id="holiday", start_day=0, end_day=0)
    problem.activities.add(id="A1", duration_in_slots=1)  # Must go in the only slot

    modeler = Modeler(problem)
    handler = FundamentalConstraintHandler(modeler)
    handler._enforce_system_breaks(problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_day_boundary_is_enforced(solve_model):
    """An activity cannot cross a day boundary."""
    # A 2-slot activity in a world with only 1 slot per day must cross a boundary
    problem = conftest.create_problem(days=2, slots_per_day=1)
    problem.activities.add(id="A1", duration_in_slots=2)

    modeler = Modeler(problem)

    # Llama al handler y método correctos
    handler = FundamentalConstraintHandler(modeler)
    handler.apply(problem)
    
    result = solve_model(modeler)
    assert result.status == cp_model.INFEASIBLE