from unittest.mock import MagicMock, patch

import pytest

from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints import preferences
from src.solver_service.protos import problem_definition_pb2 as problem_pb


@pytest.fixture(autouse=True)
def mock_utils(mocker):
    """Mocks the utility functions that are dependencies for preference constraints."""
    mocker.patch('src.solver_service.constraints.utils.create_working_status_variables', return_value=[MagicMock()])
    mocker.patch('src.solver_service.constraints.utils.count_gaps_in_schedule', return_value=MagicMock(name="num_gaps_var"))


@pytest.fixture
def mock_modeler(mocker):
    """Provides a Modeler instance with a mocked CpModel."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.days = 2
    problem.time_grid.slots_per_day = 4

    with patch('ortools.sat.python.cp_model.CpModel') as MockCpModel:
        modeler = Modeler(problem)
        modeler.model = MockCpModel()
        return modeler


# --- Tests for _apply_time_slot_preferences ---

def setup_activity_for_preference_test(modeler, act_id, pref_id):
    """Helper to add a specific activity to the modeler for testing."""
    activity = problem_pb.Activity(id=act_id, time_preference_id=pref_id)
    interval_var = MagicMock()
    interval_var.StartExpr.return_value.NotMember.return_value = MagicMock(name="not_in_domain_constraint")
    modeler.id_to_activity_map[act_id] = activity
    modeler.activity_intervals[act_id] = interval_var


def test_apply_time_slot_preferences_adds_penalty(mock_modeler):
    """
    Verifies that a penalty is added for an activity with a valid preference.
    """
    # GIVEN
    problem = mock_modeler.problem
    problem.time_preferences.add(id="pref1", preferred_slots=[0, 1], penalty_per_violation=50)
    setup_activity_for_preference_test(mock_modeler, "A1", "pref1")

    # WHEN
    preferences._apply_time_slot_preferences(mock_modeler, problem)

    # THEN
    # 1. A boolean variable was created to represent the violation.
    mock_modeler.model.NewBoolVar.assert_called_once_with("not_preferred_A1")
    is_not_preferred_var = mock_modeler.model.NewBoolVar.return_value

    # 2. A constraint linking the start time to the preferred slots was added.
    mock_start_expr = mock_modeler.activity_intervals["A1"].StartExpr()
    mock_start_expr.NotMember.assert_called_once_with([0, 1])
    not_in_domain_constraint = mock_start_expr.NotMember.return_value
    mock_modeler.model.Add.assert_called_once_with(not_in_domain_constraint)
    mock_modeler.model.Add.return_value.OnlyEnforceIf.assert_called_once_with(is_not_preferred_var)

    # 3. A penalty was added to the objective function.
    assert len(mock_modeler.objective_penalties) == 1
    assert str(mock_modeler.objective_penalties[0]) == f"({is_not_preferred_var} * 50)"


@pytest.mark.parametrize("pref_id", ["", "non_existent_pref"])
def test_apply_time_slot_preferences_skips_invalid_prefs(mock_modeler, pref_id):
    """
    Verifies no action is taken for activities with no preference ID or a
    non-existent one.
    """
    # GIVEN
    problem = mock_modeler.problem
    problem.time_preferences.add(id="pref1", preferred_slots=[0, 1], penalty_per_violation=50)
    setup_activity_for_preference_test(mock_modeler, "A1", pref_id)

    # WHEN
    preferences._apply_time_slot_preferences(mock_modeler, problem)

    # THEN
    mock_modeler.model.NewBoolVar.assert_not_called()
    mock_modeler.model.Add.assert_not_called()
    assert len(mock_modeler.objective_penalties) == 0


# --- Tests for _apply_student_group_gap_penalties ---

def test_apply_student_group_gap_penalties_adds_penalty(mock_modeler, mock_utils):
    """
    Verifies penalties are added for student groups when a penalty is defined.
    """
    # GIVEN
    problem = mock_modeler.problem
    problem.student_gap_penalty_per_day = 10
    # A group with more than one activity
    mock_modeler.group_activity_map["G1"] = [MagicMock(), MagicMock()]
    num_days = problem.time_grid.days

    # WHEN
    preferences._apply_student_group_gap_penalties(mock_modeler, problem)

    # THEN
    # 1. Utility functions were called for each day.
    assert mock_utils.create_working_status_variables.call_count == num_days
    assert mock_utils.count_gaps_in_schedule.call_count == num_days
    
    # 2. A penalty term was added to the objective for each day.
    assert len(mock_modeler.objective_penalties) == num_days
    num_gaps_var = mock_utils.count_gaps_in_schedule.return_value
    assert str(mock_modeler.objective_penalties[0]) == f"({num_gaps_var} * 10)"


def test_apply_student_group_gap_penalties_skips_if_no_penalty(mock_modeler, mock_utils):
    """Verifies no action is taken if the gap penalty is zero."""
    # GIVEN
    problem = mock_modeler.problem
    problem.student_gap_penalty_per_day = 0
    mock_modeler.group_activity_map["G1"] = [MagicMock(), MagicMock()]

    # WHEN
    preferences._apply_student_group_gap_penalties(mock_modeler, problem)

    # THEN
    mock_utils.create_working_status_variables.assert_not_called()
    mock_utils.count_gaps_in_schedule.assert_not_called()
    assert len(mock_modeler.objective_penalties) == 0

@pytest.mark.parametrize("num_activities", [0, 1])
def test_apply_student_group_gap_penalties_skips_if_insufficient_activities(mock_modeler, mock_utils, num_activities):
    """Verifies no action is taken for groups with 0 or 1 activities."""
    # GIVEN
    problem = mock_modeler.problem
    problem.student_gap_penalty_per_day = 10
    mock_modeler.group_activity_map["G1"] = [MagicMock()] * num_activities

    # WHEN
    preferences._apply_student_group_gap_penalties(mock_modeler, problem)
    
    # THEN
    mock_utils.create_working_status_variables.assert_not_called()
    mock_utils.count_gaps_in_schedule.assert_not_called()
    assert len(mock_modeler.objective_penalties) == 0
