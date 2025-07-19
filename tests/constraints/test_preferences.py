from ortools.sat.python import cp_model

from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints import preferences
from .. import conftest


def test_time_slot_preference_adds_penalty(solve_model):
    """Verifies objective is penalized for scheduling outside preferred slots."""
    problem = conftest.create_problem(days=1, slots_per_day=2)
    # Define preference for slot 0 with penalty 50
    pref = problem.time_preferences.add(id="pref1", penalty_per_violation=50)
    pref.preferred_slots.append(0)
    # Activity must be scheduled, but is locked into non-preferred slot 1
    act = problem.activities.add(id="A1", duration_in_slots=1, time_preference_id="pref1", is_locked=True)
    act.locked_start_time.day_index = 0
    act.locked_start_time.slot_index = 1

    modeler = Modeler(problem)
    preferences._apply_time_slot_preferences(modeler, problem)
    modeler.define_objective()
    result = solve_model(modeler)

    assert result.status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
    assert result.objective_value == 50


def test_student_gap_penalty_is_applied(solve_model):
    """Verifies objective is penalized for gaps in a student's schedule."""
    problem = conftest.create_problem(days=1, slots_per_day=3)
    problem.student_gap_penalty_per_day = 10
    problem.student_groups.add(id="G1")
    # Lock two activities for G1, creating one gap slot between them
    problem.activities.add(id="A1", student_group_ids=["G1"], duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})
    problem.activities.add(id="A2", student_group_ids=["G1"], duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 2})

    modeler = Modeler(problem)
    preferences._apply_student_group_gap_penalties(modeler, problem)
    modeler.define_objective()
    result = solve_model(modeler)

    assert result.status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
    # 1 gap * penalty of 10
    assert result.objective_value == 10
