from ortools.sat.python import cp_model

from src.solver_service.components.modeler import Modeler
from src.solver_service.handlers.structural_handler import StructuralConstraintHandler

from .. import conftest

def test_activity_ordering_is_enforced(solve_model):
    """Activity A must end before Activity B begins."""
    problem = conftest.create_problem(days=1, slots_per_day=2)
    problem.activity_orderings.add(before_activity_id="A1", after_activity_id="A2")
    # Lock A2 at the start, making it impossible for A1 to come before
    problem.activities.add(id="A1", duration_in_slots=1)
    problem.activities.add(
        id="A2",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )

    modeler = Modeler(problem)
    handler = StructuralConstraintHandler(modeler)
    handler._enforce_activity_ordering(problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_consecutive_activities_are_enforced(solve_model):
    """Activity A must be immediately followed by Activity B."""
    problem = conftest.create_problem(days=1, slots_per_day=3)
    problem.consecutive_activities.add(first_activity_id="A1", second_activity_id="A2")
    # Lock A1 and A2 with a gap, violating the consecutive constraint
    problem.activities.add(
        id="A1",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )
    problem.activities.add(
        id="A2",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 2},
    )

    modeler = Modeler(problem)
    handler = StructuralConstraintHandler(modeler)
    handler._enforce_consecutive_activities(problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_min_days_between_is_enforced(solve_model):
    """A minimum number of days must separate two activities."""
    problem = conftest.create_problem(days=2, slots_per_day=1)
    problem.min_days_between_activities.add(
        first_activity_id="A1", second_activity_id="A2", minimum_days=2
    )
    # Lock activities on adjacent days, violating the min_days=2 rule
    problem.activities.add(
        id="A1",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 0, "slot_index": 0},
    )
    problem.activities.add(
        id="A2",
        duration_in_slots=1,
        is_locked=True,
        locked_start_time={"day_index": 1, "slot_index": 0},
    )

    modeler = Modeler(problem)
    handler = StructuralConstraintHandler(modeler)
    handler._enforce_min_days_between(problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE
