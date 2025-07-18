import pytest
from unittest.mock import MagicMock, patch

from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints import workload
from src.solver_service.protos import problem_definition_pb2 as problem_pb

# Use a module-level patcher to mock dependencies for all tests in this file.
@pytest.fixture(autouse=True)
def mock_utils(mocker):
    """Mocks the utility functions that are dependencies for workload constraints."""
    mocker.patch('src.solver_service.constraints.utils.get_day_active_literals', return_value=[MagicMock()])
    mocker.patch('src.solver_service.constraints.utils.create_working_status_variables', return_value=[MagicMock()])
    mocker.patch('src.solver_service.constraints.utils.count_gaps_in_schedule', return_value=MagicMock())


@pytest.fixture
def mock_modeler(mocker):
    """Provides a Modeler instance with a mocked CpModel."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.days = 5
    problem.time_grid.slots_per_day = 8

    # Patch the model creation within the Modeler to avoid OR-Tools dependency
    with patch('ortools.sat.python.cp_model.CpModel') as MockCpModel:
        modeler = Modeler(problem)
        modeler.model = MockCpModel()
        
        # Pre-populate with a sample activity
        activity = problem_pb.Activity(id="A1", duration_in_slots=2)
        interval_var = MagicMock()
        modeler.interval_to_activity_map[interval_var] = activity
        modeler.teacher_activity_map["T1"] = [interval_var]
        
        return modeler

# --- Tests for _apply_max_hours_per_day ---

def test_apply_max_hours_per_day(mock_modeler):
    """
    Verifies that a 'sum(durations * is_on_day) <= max_hours' constraint is
    added for each day.
    """
    # GIVEN
    problem = mock_modeler.problem
    constraint = problem_pb.WorkloadConstraint(teacher_id="T1", max_hours_per_day=3)
    teacher_intervals = mock_modeler.teacher_activity_map["T1"]

    # WHEN
    workload._apply_max_hours_per_day(mock_modeler, problem, constraint, teacher_intervals)

    # THEN
    # The constraint should be added for each of the 5 days in the time grid.
    assert mock_modeler.model.Add.call_count == 5
    
    # Check the content of one of the calls. It should sum the products of
    # duration and the mocked 'is_on_day' literal.
    last_call_args = mock_modeler.model.Add.call_args.args[0]
    assert str(last_call_args) == "((2 * Mock()) <= 3)"


# --- Tests for _apply_max_gaps_per_day ---

def test_apply_max_gaps_per_day_adds_penalty(mock_modeler):
    """
    Verifies that a penalty term is added to the objective when penalty_per_gap > 0.
    """
    # GIVEN
    problem = mock_modeler.problem
    constraint = problem_pb.WorkloadConstraint(
        teacher_id="T1", max_gaps_per_day=1, penalty_per_gap=10
    )
    teacher_intervals = mock_modeler.teacher_activity_map["T1"]
    
    # WHEN
    workload._apply_max_gaps_per_day(mock_modeler, problem, constraint, teacher_intervals)

    # THEN
    # A penalty term should be added for each of the 5 days.
    assert len(mock_modeler.objective_penalties) == 5
    
    # Check the structure of the penalty expression.
    penalty_expr = mock_modeler.objective_penalties[0]
    assert str(penalty_expr) == "(Mock() * 10)" # (over_max_gaps * penalty_per_gap)


def test_apply_max_gaps_per_day_adds_no_penalty_if_zero(mock_modeler):
    """Verifies that no penalty is added if penalty_per_gap is zero."""
    # GIVEN
    problem = mock_modeler.problem
    constraint = problem_pb.WorkloadConstraint(teacher_id="T1", penalty_per_gap=0)
    teacher_intervals = mock_modeler.teacher_activity_map["T1"]

    # WHEN
    workload._apply_max_gaps_per_day(mock_modeler, problem, constraint, teacher_intervals)

    # THEN
    assert len(mock_modeler.objective_penalties) == 0


# --- Tests for _apply_max_hours_per_week ---

def test_apply_max_hours_per_week(mock_modeler):
    """
    Verifies a simple 'sum(durations) <= max_hours' constraint is added.
    """
    # GIVEN
    constraint = problem_pb.AdvancedWorkloadConstraint(max_hours_per_week=10)
    # Add another activity for T1 to make the sum interesting
    activity2 = problem_pb.Activity(id="A2", duration_in_slots=3)
    interval2 = MagicMock()
    mock_modeler.interval_to_activity_map[interval2] = activity2
    teacher_intervals = mock_modeler.teacher_activity_map["T1"] + [interval2]

    # WHEN
    workload._apply_max_hours_per_week(mock_modeler, constraint, teacher_intervals)

    # THEN
    # The sum of durations (2 + 3) should be constrained.
    mock_modeler.model.Add.assert_called_once_with(5 <= 10)


# --- Tests for _apply_max_days_per_week ---

def test_apply_max_days_per_week(mock_modeler):
    """
    Verifies that 'sum(is_working_on_day_flags) <= max_days' is added.
    """
    # GIVEN
    problem = mock_modeler.problem
    constraint = problem_pb.AdvancedWorkloadConstraint(teacher_id="T1", max_days_per_week=3)
    teacher_intervals = mock_modeler.teacher_activity_map["T1"]
    
    # WHEN
    workload._apply_max_days_per_week(mock_modeler, problem, constraint, teacher_intervals)

    # THEN
    # It should create one 'is_working_on_day' flag per day (5 days).
    num_days = problem.time_grid.days
    new_bool_var_calls = [
        call for call in mock_modeler.model.NewBoolVar.call_args_list
        if call.args[0].startswith('tT1_working_day_')
    ]
    assert len(new_bool_var_calls) == num_days
    
    # A final constraint summing these flags should be added.
    # The mock for AddBoolOr means the flags list passed to sum() will be populated.
    last_call_args = mock_modeler.model.Add.call_args.args[0]
    # The string representation checks for a sum of 5 mock objects <= 3
    assert " + " in str(last_call_args)
    assert str(last_call_args).count("Mock()") == 5
    assert str(last_call_args).endswith("<= 3)")
