from typing import List

from src.solver_service.components.modeler import Modeler
from src.solver_service.protos import problem_definition_pb2 as problem_pb
from . import utils


def apply_all_workload_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """Applies all teacher-specific workload constraints."""
    _apply_basic_workload_constraints(modeler, problem)
    _apply_advanced_workload_constraints(modeler, problem)


def _apply_basic_workload_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """Applies daily workload constraints from the `WorkloadConstraint` message."""
    for constraint in problem.workload_constraints:
        teacher_intervals = modeler.teacher_activity_map.get(constraint.teacher_id, [])
        if not teacher_intervals:
            continue
        if constraint.max_hours_per_day > 0:
            _apply_max_hours_per_day(modeler, problem, constraint, teacher_intervals)
        if constraint.max_gaps_per_day >= 0:
            _apply_max_gaps_per_day(modeler, problem, constraint, teacher_intervals)


def _apply_advanced_workload_constraints(modeler: Modeler, problem: problem_pb.ProblemDefinition) -> None:
    """Applies weekly workload constraints from the `AdvancedWorkloadConstraint` message."""
    for constraint in problem.advanced_workload_constraints:
        teacher_intervals = modeler.teacher_activity_map.get(constraint.teacher_id, [])
        if not teacher_intervals:
            continue
        if constraint.max_hours_per_week > 0:
            _apply_max_hours_per_week(modeler, constraint, teacher_intervals)
        if constraint.max_days_per_week > 0:
            _apply_max_days_per_week(modeler, problem, constraint, teacher_intervals)


# A teacher should not be scheduled for more than X hours on any given day.
def _apply_max_hours_per_day(modeler: Modeler, problem: problem_pb.ProblemDefinition,
                             constraint: problem_pb.WorkloadConstraint, teacher_intervals: List) -> None:
    """Enforces maximum working hours per day for a teacher."""
    slots_per_day = problem.time_grid.slots_per_day
    for day in range(problem.time_grid.days):
        daily_workload = []
        for interval in teacher_intervals:
            activity = modeler.interval_to_activity_map[interval]
            is_on_day = modeler.model.NewBoolVar(f"{interval.Name()}_on_day_{day}")
            start_of_day = day * slots_per_day
            end_of_day = start_of_day + slots_per_day

            modeler.model.Add(interval.StartExpr() >= start_of_day).OnlyEnforceIf(is_on_day)
            modeler.model.Add(interval.StartExpr() < end_of_day).OnlyEnforceIf(is_on_day)

            daily_workload.append(activity.duration_in_slots * is_on_day)

        if daily_workload:
            modeler.model.Add(sum(daily_workload) <= constraint.max_hours_per_day)


# for Students and Teachers, A schedule with many single-hour gaps is frustrating
def _apply_max_gaps_per_day(modeler: Modeler, problem: problem_pb.ProblemDefinition,
                            constraint: problem_pb.WorkloadConstraint, teacher_intervals: List) -> None:
    """Applies soft constraint for maximum gaps per day."""
    slots_per_day = problem.time_grid.slots_per_day
    for day in range(problem.time_grid.days):
        is_working = utils.create_working_status_variables(
            modeler.model, constraint.teacher_id, teacher_intervals, day, slots_per_day
        )
        num_gaps = utils.count_gaps_in_schedule(
            modeler.model, constraint.teacher_id, day, is_working
        )

        if constraint.penalty_per_gap > 0:
            over_max_gaps = modeler.model.NewIntVar(0, slots_per_day, f"{constraint.teacher_id}_day{day}_over_gaps")
            modeler.model.Add(over_max_gaps >= num_gaps - constraint.max_gaps_per_day)
            modeler.objective_penalties.append(over_max_gaps * constraint.penalty_per_gap)


# A teacher's total scheduled hours must not exceed their contractual limit.
def _apply_max_hours_per_week(modeler: Modeler, constraint: problem_pb.AdvancedWorkloadConstraint,
                              teacher_intervals: List) -> None:
    """Enforces maximum working hours per week."""
    weekly_demands = [modeler.interval_to_activity_map[interval].duration_in_slots for interval in teacher_intervals]
    modeler.model.Add(sum(weekly_demands) <= constraint.max_hours_per_week)


# A teacher should not be forced to come in 5 days a week if their workload only requires 3
def _apply_max_days_per_week(modeler: Modeler, problem: problem_pb.ProblemDefinition,
                             constraint: problem_pb.AdvancedWorkloadConstraint, teacher_intervals: List) -> None:
    """Enforces maximum working days per week."""
    slots_per_day = problem.time_grid.slots_per_day
    days_working = []
    for day in range(problem.time_grid.days):
        day_working = modeler.model.NewBoolVar(f"{constraint.teacher_id}_working_day_{day}")
        start_of_day = day * slots_per_day
        end_of_day = start_of_day + slots_per_day

        day_activities_literals = []
        for interval in teacher_intervals:
            on_this_day = modeler.model.NewBoolVar(f"{interval.Name()}_on_day_{day}_advanced")
            modeler.model.Add(interval.StartExpr() >= start_of_day).OnlyEnforceIf(on_this_day)
            modeler.model.Add(interval.StartExpr() < end_of_day).OnlyEnforceIf(on_this_day)
            day_activities_literals.append(on_this_day)

        if day_activities_literals:
            modeler.model.AddBoolOr(day_activities_literals).OnlyEnforceIf(day_working)
            modeler.model.Add(day_working == 0).OnlyEnforceIf([lit.Not() for lit in day_activities_literals])
        else:
            modeler.model.Add(day_working == 0)

        days_working.append(day_working)

    modeler.model.Add(sum(days_working) <= constraint.max_days_per_week)
