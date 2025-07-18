import pytest
from unittest.mock import MagicMock, patch, call

# Assume a project structure where 'src' is on the python path
from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints.fundamental import (
    _apply_teacher_conflicts,
    _apply_student_group_conflicts,
    _apply_teacher_unavailability,
    _apply_system_breaks,
    _validate_constraints,
)
from src.solver_service.protos import problem_definition_pb2 as problem_pb


@pytest.fixture
def mock_modeler(mocker):
    """Provides a Modeler instance with a mocked CpModel."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.slots_per_day = 8

    with patch('ortools.sat.python.cp_model.CpModel') as MockCpModel:
        modeler = Modeler(problem)
        modeler.model = MockCpModel()
        return modeler


# --- Test for _validate_constraints ---

def test_validate_constraints_raises_error_on_invalid_input():
    """Verifies that validation catches impossible constraint values."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.slots_per_day = 8
    constraint = problem.workload_constraints.add()
    constraint.teacher_id = "T1"
    constraint.max_hours_per_day = 9  # Impossible

    with pytest.raises(ValueError, match="exceeds slots_per_day"):
        _validate_constraints(problem)


def test_validate_constraints_passes_on_valid_input():
    """Verifies that validation allows correct constraint values."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.slots_per_day = 8
    constraint = problem.workload_constraints.add()
    constraint.teacher_id = "T1"
    constraint.max_hours_per_day = 8  # Valid

    try:
        _validate_constraints(problem)
    except ValueError:
        pytest.fail("Validation raised ValueError unexpectedly.")


# --- Test for _apply_teacher_conflicts (from previous step) ---

@pytest.mark.parametrize(
    "test_id, activities_per_teacher, expected_call_count, expected_interval_counts",
    [
        ("NO_CONFLICTS", {"T1": 1, "T2": 1, "T3": 0}, 0, []),
        ("SINGLE_CONFLICT", {"T1": 3, "T2": 1}, 1, [3]),
        ("MULTIPLE_CONFLICTS", {"T1": 2, "T2": 1, "T3": 4}, 2, [2, 4]),
    ]
)
def test_apply_teacher_conflicts(
        mock_modeler, test_id, activities_per_teacher, expected_call_count, expected_interval_counts
):
    """Validates that AddNoOverlap is called correctly for teacher assignments."""
    for teacher_id, num_activities in activities_per_teacher.items():
        mock_modeler.teacher_activity_map[teacher_id] = [MagicMock() for _ in range(num_activities)]

    _apply_teacher_conflicts(mock_modeler)

    mock_add_no_overlap = mock_modeler.model.AddNoOverlap
    assert mock_add_no_overlap.call_count == expected_call_count
    if expected_call_count > 0:
        actual_counts = sorted([len(c.args[0]) for c in mock_add_no_overlap.call_args_list])
        assert actual_counts == sorted(expected_interval_counts)


# --- Test for _apply_student_group_conflicts ---

@pytest.mark.parametrize(
    "test_id, activities_per_group, expected_call_count, expected_interval_counts",
    [
        ("NO_CONFLICTS", {"G1": 1, "G2": 0}, 0, []),
        ("SINGLE_CONFLICT", {"G1": 4, "G2": 1}, 1, [4]),
        ("MULTIPLE_CONFLICTS", {"G1": 2, "G2": 3}, 2, [2, 3]),
    ]
)
def test_apply_student_group_conflicts(
        mock_modeler, test_id, activities_per_group, expected_call_count, expected_interval_counts
):
    """Validates that AddNoOverlap is called correctly for student group assignments."""
    for group_id, num_activities in activities_per_group.items():
        mock_modeler.group_activity_map[group_id] = [MagicMock() for _ in range(num_activities)]

    _apply_student_group_conflicts(mock_modeler)

    mock_add_no_overlap = mock_modeler.model.AddNoOverlap
    assert mock_add_no_overlap.call_count == expected_call_count
    if expected_call_count > 0:
        actual_counts = sorted([len(c.args[0]) for c in mock_add_no_overlap.call_args_list])
        assert actual_counts == sorted(expected_interval_counts)


# --- Test for _apply_teacher_unavailability ---

def test_apply_teacher_unavailability(mock_modeler):
    """
    Validates that unavailable slots are converted to fixed intervals and added
    to the teacher's NoOverlap constraint.
    """
    # GIVEN: A teacher 'T1' with 2 activities and 2 unavailable slots.
    problem = mock_modeler.problem
    teacher = problem.teachers.add(id="T1")
    teacher.unavailable_slots.add(day_index=0, slot_index=1)
    teacher.unavailable_slots.add(day_index=1, slot_index=3)

    activity_intervals = [MagicMock(), MagicMock()]
    mock_modeler.teacher_activity_map["T1"] = activity_intervals

    # WHEN: The constraint is applied
    _apply_teacher_unavailability(mock_modeler, problem)

    # THEN:
    # 1. NewFixedSizeIntervalVar was called twice for the unavailable slots.
    mock_new_interval = mock_modeler.model.NewFixedSizeIntervalVar
    assert mock_new_interval.call_count == 2
    mock_new_interval.assert_has_calls([
        call(start=1, size=1, name='forbidden_T1_0_1'),
        call(start=11, size=1, name='forbidden_T1_1_3')
    ], any_order=True)

    # 2. AddNoOverlap was called once with all intervals (2 activities + 2 forbidden).
    mock_add_no_overlap = mock_modeler.model.AddNoOverlap
    mock_add_no_overlap.assert_called_once()
    assert len(mock_add_no_overlap.call_args.args[0]) == 4


def test_apply_teacher_unavailability_does_nothing_if_no_slots(mock_modeler):
    """Verifies no action is taken if a teacher has no unavailable slots."""
    problem = mock_modeler.problem
    problem.teachers.add(id="T1")
    mock_modeler.teacher_activity_map["T1"] = [MagicMock()]

    _apply_teacher_unavailability(mock_modeler, problem)

    mock_modeler.model.NewFixedSizeIntervalVar.assert_not_called()
    mock_modeler.model.AddNoOverlap.assert_not_called()


# --- Test for _apply_system_breaks ---
def test_apply_system_breaks(mock_modeler):
    """Validates that system breaks add NoOverlap constraints for all activities."""
    # GIVEN: Two activities and one system break spanning 2 days.
    problem = mock_modeler.problem
    problem.system_breaks.add(id="holiday", start_day=1, end_day=2)  # Days 1 and 2

    activity_intervals = [MagicMock(), MagicMock()]
    mock_modeler.activity_intervals = {"A1": activity_intervals[0], "A2": activity_intervals[1]}

    # WHEN: The constraint is applied
    _apply_system_breaks(mock_modeler, problem)

    # THEN:
    # 1. A single fixed interval is created for the break using positional args.
    mock_modeler.model.NewFixedSizeIntervalVar.assert_called_once_with(
        8, 16, 'break_holiday'
    )
    break_interval = mock_modeler.model.NewFixedSizeIntervalVar.return_value

    # 2. AddNoOverlap is called twice, once for each activity against the break interval.
    mock_modeler.model.AddNoOverlap.assert_has_calls([
        call([break_interval, activity_intervals[0]]),
        call([break_interval, activity_intervals[1]])
    ], any_order=True)


def test_apply_system_breaks_does_nothing_if_no_breaks(mock_modeler):
    """Verifies no action is taken if there are no system breaks."""
    mock_modeler.activity_intervals = {"A1": MagicMock()}

    _apply_system_breaks(mock_modeler, mock_modeler.problem)

    mock_modeler.model.NewFixedSizeIntervalVar.assert_not_called()
    mock_modeler.model.AddNoOverlap.assert_not_called()
