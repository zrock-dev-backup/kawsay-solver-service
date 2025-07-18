import pytest
from unittest.mock import MagicMock, patch, call

from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints import structural
from src.solver_service.protos import problem_definition_pb2 as problem_pb


@pytest.fixture
def mock_modeler():
    """Provides a Modeler instance with a mocked CpModel."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.days = 5
    problem.time_grid.slots_per_day = 8

    with patch('ortools.sat.python.cp_model.CpModel') as MockCpModel:
        modeler = Modeler(problem)
        modeler.model = MockCpModel()
        return modeler


def setup_modeler_for_relations(modeler: Modeler, activity_ids: list[str]):
    """Helper to populate a modeler with mock activities and intervals."""
    for act_id in activity_ids:
        activity = problem_pb.Activity(id=act_id)
        interval_var = MagicMock()
        interval_var.StartExpr.return_value = MagicMock(name=f"start_{act_id}")
        interval_var.EndExpr.return_value = MagicMock(name=f"end_{act_id}")

        modeler.id_to_activity_map[act_id] = activity
        modeler.activity_intervals[act_id] = interval_var


# --- Test for _apply_day_boundary_constraints ---

def test_apply_day_boundary_constraints(mock_modeler):
    """
    Verifies that start_day == end_day constraint is added for an activity.
    """
    # GIVEN
    setup_modeler_for_relations(mock_modeler, ["A1"])
    problem = mock_modeler.problem
    mock_start_expr = mock_modeler.activity_intervals["A1"].StartExpr()
    mock_end_expr = mock_modeler.activity_intervals["A1"].EndExpr()

    # WHEN
    structural._apply_day_boundary_constraints(mock_modeler, problem)

    # THEN
    mock_add = mock_modeler.model.Add
    mock_add_division = mock_modeler.model.AddDivision

    # It should create day variables for start and end
    mock_add_division.assert_has_calls([
        call(target=mock_modeler.model.NewIntVar(), expr=mock_start_expr, mod=8),
        call(target=mock_modeler.model.NewIntVar(), expr=mock_end_expr - 1, mod=8)
    ], any_order=True)

    # It should add the final equality constraint
    last_call_args = mock_add.call_args.args
    equality_constraint = last_call_args[0]
    assert equality_constraint.left == equality_constraint.right


def test_day_boundary_skipped_for_long_activities(mock_modeler):
    """
    Verifies the day boundary constraint is skipped if an activity is longer
    than a day.
    """
    # GIVEN
    problem = mock_modeler.problem
    problem.time_grid.slots_per_day = 8
    activity = problem_pb.Activity(id="A1", duration_in_slots=9)
    mock_modeler.id_to_activity_map["A1"] = activity
    mock_modeler.activity_intervals["A1"] = MagicMock()

    # WHEN
    structural._apply_day_boundary_constraints(mock_modeler, problem)

    # THEN
    mock_modeler.model.AddDivision.assert_not_called()
    mock_modeler.model.Add.assert_not_called()


# --- Test for _apply_activity_ordering ---

def test_apply_activity_ordering(mock_modeler):
    """Verifies 'before.End <= after.Start' constraint is added."""
    # GIVEN
    problem = mock_modeler.problem
    problem.activity_orderings.add(
        before_activity_id="A1", after_activity_id="A2"
    )
    setup_modeler_for_relations(mock_modeler, ["A1", "A2"])

    # WHEN
    structural._apply_activity_ordering(mock_modeler, problem)

    # THEN
    mock_modeler.model.Add.assert_called_once_with("end_A1" <= "start_A2")


# --- Test for _apply_consecutive_activities ---

def test_apply_consecutive_activities(mock_modeler):
    """Verifies 'first.End == second.Start' constraint is added."""
    # GIVEN
    problem = mock_modeler.problem
    problem.consecutive_activities.add(
        first_activity_id="A1", second_activity_id="A2"
    )
    setup_modeler_for_relations(mock_modeler, ["A1", "A2"])

    # WHEN
    structural._apply_consecutive_activities(mock_modeler, problem)

    # THEN
    mock_modeler.model.Add.assert_called_once_with("end_A1" == "start_A2")


# --- Test for _apply_min_days_between_activities ---

def test_apply_min_days_between_activities(mock_modeler):
    """Verifies 'abs(day1 - day2) >= min_days' constraint is added."""
    # GIVEN
    problem = mock_modeler.problem
    problem.min_days_between_activities.add(
        first_activity_id="A1", second_activity_id="A2", minimum_days=3
    )
    setup_modeler_for_relations(mock_modeler, ["A1", "A2"])

    # WHEN
    structural._apply_min_days_between_activities(mock_modeler, problem)

    # THEN
    mock_add_division = mock_modeler.model.AddDivision
    # CORRECTED: Assert call to AddAbsEquality, not a non-existent AddAbs
    mock_add_abs_eq = mock_modeler.model.AddAbsEquality

    # It calculates the day for each activity
    mock_add_division.assert_has_calls([
        call(mock_modeler.model.NewIntVar(), mock_modeler.activity_intervals["A1"].StartExpr(), 8),
        call(mock_modeler.model.NewIntVar(), mock_modeler.activity_intervals["A2"].StartExpr(), 8)
    ], any_order=True)

    # It adds the absolute difference constraint
    day1_var = mock_add_division.call_args_list[0].args[0]
    day2_var = mock_add_division.call_args_list[1].args[0]

    # Check that AddAbsEquality was called with a new target variable and the day difference
    mock_add_abs_eq.assert_called_once()
    abs_eq_call_args = mock_add_abs_eq.call_args.args
    day_diff_var = abs_eq_call_args[0]
    assert abs_eq_call_args[1] == day1_var - day2_var

    # Check that the final constraint uses this new variable
    mock_modeler.model.Add.assert_called_once_with(day_diff_var >= 3)