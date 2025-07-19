from ortools.sat.python import cp_model

from src.solver_service.components.modeler import Modeler
from src.solver_service.constraints import workload
from .. import conftest


def test_max_hours_per_day_is_enforced(solve_model):
    """Teacher's daily work hours cannot exceed the maximum."""
    problem = conftest.create_problem(days=1, slots_per_day=4)
    problem.teachers.add(id="T1")
    # Two 2-hour activities (4 hours total) for a teacher who can only work 3 hours
    problem.activities.add(id="A1", teacher_id="T1", duration_in_slots=2)
    problem.activities.add(id="A2", teacher_id="T1", duration_in_slots=2)
    problem.workload_constraints.add(teacher_id="T1", max_hours_per_day=3)

    modeler = Modeler(problem)
    workload._apply_basic_workload_constraints(modeler, problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_max_gaps_per_day_adds_penalty(solve_model):
    """Penalizes gaps in a teacher's daily schedule."""
    problem = conftest.create_problem(days=1, slots_per_day=3)
    problem.teachers.add(id="T1")
    # Lock two activities with a gap, for a teacher who should have 0 gaps
    problem.activities.add(id="A1", teacher_id="T1", duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})
    problem.activities.add(id="A2", teacher_id="T1", duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 2})
    problem.workload_constraints.add(teacher_id="T1", max_gaps_per_day=0, penalty_per_gap=25)

    modeler = Modeler(problem)
    workload._apply_basic_workload_constraints(modeler, problem)
    modeler.define_objective()
    result = solve_model(modeler)

    assert result.status in [cp_model.OPTIMAL, cp_model.FEASIBLE]
    # 1 gap * penalty of 25
    assert result.objective_value == 25


def test_max_hours_per_week_is_enforced(solve_model):
    """Teacher's total work hours cannot exceed the weekly maximum."""
    problem = conftest.create_problem(days=5, slots_per_day=1)
    problem.teachers.add(id="T1")
    # 5 hours of work for a teacher contracted for 4 hours
    problem.activities.add(id="A1", teacher_id="T1", duration_in_slots=2)
    problem.activities.add(id="A2", teacher_id="T1", duration_in_slots=3)
    problem.advanced_workload_constraints.add(teacher_id="T1", max_hours_per_week=4)

    modeler = Modeler(problem)
    workload._apply_advanced_workload_constraints(modeler, problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE


def test_max_days_per_week_is_enforced(solve_model):
    """Teacher cannot work more than the maximum number of days."""
    problem = conftest.create_problem(days=3, slots_per_day=1)
    problem.teachers.add(id="T1")
    # Lock activities on 2 different days for a teacher who can only work 1 day
    problem.activities.add(id="A1", teacher_id="T1", duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 0, 'slot_index': 0})
    problem.activities.add(id="A2", teacher_id="T1", duration_in_slots=1, is_locked=True, locked_start_time={'day_index': 1, 'slot_index': 0})
    problem.advanced_workload_constraints.add(teacher_id="T1", max_days_per_week=1)

    modeler = Modeler(problem)
    workload._apply_advanced_workload_constraints(modeler, problem)
    result = solve_model(modeler)

    assert result.status == cp_model.INFEASIBLE
