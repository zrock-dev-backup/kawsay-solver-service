from typing import List
from ortools.sat.python import cp_model

from ..protos import problem_definition_pb2 as problem_pb
from .base_handler import BaseConstraintHandler


class WorkloadConstraintHandler(BaseConstraintHandler):
    """
    Applies all teacher-specific workload constraints.
    - Hard constraints: max hours/day, max hours/week, max days/week.
    - Soft constraints: penalties for excessive gaps in a daily schedule.
    """
    def apply(self, problem: problem_pb.ProblemDefinition) -> None:
        self._apply_basic_workload(problem)
        self._apply_advanced_workload(problem)

    def _apply_basic_workload(self, problem: problem_pb.ProblemDefinition) -> None:
        """Applies daily workload constraints from the `WorkloadConstraint` message."""
        for constraint in problem.workload_constraints:
            teacher_intervals = self._modeler.teacher_activity_map.get(constraint.teacher_id)
            if not teacher_intervals:
                continue

            if constraint.max_hours_per_day > 0:
                self._enforce_max_hours_per_day(
                    problem, constraint.teacher_id, teacher_intervals, constraint.max_hours_per_day
                )

            if constraint.penalty_per_gap > 0 and constraint.max_gaps_per_day >= 0:
                self._penalize_daily_gaps(
                    problem,
                    entity_id=f"teacher_{constraint.teacher_id}",
                    intervals=teacher_intervals,
                    max_gaps=constraint.max_gaps_per_day,
                    penalty=constraint.penalty_per_gap
                )

    def _apply_advanced_workload(self, problem: problem_pb.ProblemDefinition) -> None:
        """Applies weekly workload constraints from the `AdvancedWorkloadConstraint` message."""
        for constraint in problem.advanced_workload_constraints:
            teacher_intervals = self._modeler.teacher_activity_map.get(constraint.teacher_id)
            if not teacher_intervals:
                continue

            if constraint.max_hours_per_week > 0:
                self._enforce_max_hours_per_week(teacher_intervals, constraint.max_hours_per_week)

            if constraint.max_days_per_week > 0:
                self._enforce_max_days_per_week(
                    problem, constraint.teacher_id, teacher_intervals, constraint.max_days_per_week
                )

    # =========================================================================
    # Private Implementation Methods
    # =========================================================================

    def _enforce_max_hours_per_day(self, problem: problem_pb.ProblemDefinition, teacher_id: str, intervals: list, max_hours: int) -> None:
        for day in range(problem.time_grid.days):
            daily_load = []
            for interval in intervals:
                is_on_day = self._is_interval_on_day(interval, day, problem.time_grid.slots_per_day, f"t{teacher_id}_maxhrs_day{day}")
                activity = self._modeler.interval_to_activity_map[interval]
                daily_load.append(activity.duration_in_slots * is_on_day)
            self._model.Add(sum(daily_load) <= max_hours)

    def _enforce_max_hours_per_week(self, intervals: list, max_hours: int) -> None:
        total_duration = sum(self._modeler.interval_to_activity_map[i].duration_in_slots for i in intervals)
        self._model.Add(total_duration <= max_hours)

    def _enforce_max_days_per_week(self, problem: problem_pb.ProblemDefinition, teacher_id: str, intervals: list, max_days: int) -> None:
        days_working_flags = []
        for day in range(problem.time_grid.days):
            is_active_on_day = self._model.NewBoolVar(f"t{teacher_id}_active_on_day_{day}")
            literals = [self._is_interval_on_day(i, day, problem.time_grid.slots_per_day, f"t{teacher_id}_maxdays_day{day}") for i in intervals]
            
            if literals:
                self._model.AddBoolOr(literals).OnlyEnforceIf(is_active_on_day)
                self._model.Add(is_active_on_day == 0).OnlyEnforceIf([lit.Not() for lit in literals])
            else:
                 self._model.Add(is_active_on_day == 0)
            days_working_flags.append(is_active_on_day)
        
        if days_working_flags:
            self._model.Add(sum(days_working_flags) <= max_days)

    def _penalize_daily_gaps(self, problem: problem_pb.ProblemDefinition, entity_id: str, intervals: List, max_gaps: int, penalty: int) -> None:
        if len(intervals) <= 1:
            return

        for day in range(problem.time_grid.days):
            is_working_slots = self._get_working_slots_for_day(problem, entity_id, intervals, day)
            num_gaps = self._count_gaps_in_schedule(problem, entity_id, day, is_working_slots)

            over_max_gaps = self._model.NewIntVar(0, problem.time_grid.slots_per_day, f"{entity_id}_day{day}_over_gaps")
            self._model.Add(over_max_gaps >= num_gaps - max_gaps)
            self._model.Add(over_max_gaps >= 0) # Ensure non-negative

            self._modeler.objective_penalties.append(over_max_gaps * penalty)

    def _is_interval_on_day(self, interval: cp_model.IntervalVar, day: int, slots_per_day: int, prefix: str) -> cp_model.IntVar:
        """Returns a boolean variable that is true iff the interval starts on the given day."""
        start_of_day = day * slots_per_day
        end_of_day = start_of_day + slots_per_day
        is_on_day = self._model.NewBoolVar(f"{prefix}_{interval.Name()}")
        start_var = interval.StartExpr()

        lit1 = self._model.NewBoolVar(f"{is_on_day.Name()}_ge")
        self._model.Add(start_var >= start_of_day).OnlyEnforceIf(lit1)
        self._model.Add(start_var < start_of_day).OnlyEnforceIf(lit1.Not())

        lit2 = self._model.NewBoolVar(f"{is_on_day.Name()}_lt")
        self._model.Add(start_var < end_of_day).OnlyEnforceIf(lit2)
        self._model.Add(start_var >= end_of_day).OnlyEnforceIf(lit2.Not())

        self._model.AddBoolAnd([lit1, lit2]).OnlyEnforceIf(is_on_day)
        self._model.AddImplication(is_on_day.Not(), lit1.Not()).OnlyEnforceIf(lit2)
        self._model.AddImplication(is_on_day.Not(), lit2.Not()).OnlyEnforceIf(lit1)
        return is_on_day
    
    def _get_working_slots_for_day(self, problem: problem_pb.ProblemDefinition, entity_id: str, intervals: list, day: int) -> List[cp_model.IntVar]:
        """Creates a list of booleans, one for each slot of the day, indicating if the entity is active."""
        slots_per_day = problem.time_grid.slots_per_day
        start_of_day = day * slots_per_day
        is_working_per_slot = []
        
        for slot_idx in range(slots_per_day):
            current_slot = start_of_day + slot_idx
            is_working_slot = self._model.NewBoolVar(f"{entity_id}_day{day}_slot{slot_idx}_working")
            
            literals_for_slot = []
            for interval in intervals:
                lit = self._model.NewBoolVar(f"{interval.Name()}_covers_{day}_{slot_idx}")
                
                # Reify lit <=> (interval.Start() <= current_slot < interval.End())
                start_cond = self._model.NewBoolVar(f"{lit.Name()}_c1")
                self._model.Add(interval.StartExpr() <= current_slot).OnlyEnforceIf(start_cond)
                self._model.Add(interval.StartExpr() > current_slot).OnlyEnforceIf(start_cond.Not())

                end_cond = self._model.NewBoolVar(f"{lit.Name()}_c2")
                self._model.Add(current_slot < interval.EndExpr()).OnlyEnforceIf(end_cond)
                self._model.Add(current_slot >= interval.EndExpr()).OnlyEnforceIf(end_cond.Not())

                self._model.AddBoolAnd([start_cond, end_cond]).OnlyEnforceIf(lit)
                self._model.AddImplication(lit.Not(), start_cond.Not()).OnlyEnforceIf(end_cond)
                self._model.AddImplication(lit.Not(), end_cond.Not()).OnlyEnforceIf(start_cond)

                literals_for_slot.append(lit)
            
            if literals_for_slot:
                self._model.AddBoolOr(literals_for_slot).OnlyEnforceIf(is_working_slot)
                self._model.Add(is_working_slot == 0).OnlyEnforceIf([l.Not() for l in literals_for_slot])
            else:
                self._model.Add(is_working_slot == 0)
            is_working_per_slot.append(is_working_slot)
        
        return is_working_per_slot

    def _count_gaps_in_schedule(self, problem: problem_pb.ProblemDefinition, entity_id: str, day: int, is_working_slots: List[cp_model.IntVar]) -> cp_model.IntVar:
        slots_per_day = len(is_working_slots)
        
        first = self._model.NewIntVar(-1, slots_per_day - 1, f"{entity_id}_day{day}_first")
        last = self._model.NewIntVar(-1, slots_per_day - 1, f"{entity_id}_day{day}_last")
        
        for i in range(slots_per_day):
            self._model.Add(first == i).OnlyEnforceIf(is_working_slots[i]).OnlyEnforceIf(
                [is_working_slots[j].Not() for j in range(i)])
            self._model.Add(last == i).OnlyEnforceIf(is_working_slots[i]).OnlyEnforceIf(
                [is_working_slots[j].Not() for j in range(i + 1, slots_per_day)])

        no_work = self._model.NewBoolVar(f"{entity_id}_day{day}_no_work")
        self._model.Add(sum(is_working_slots) == 0).OnlyEnforceIf(no_work)
        self._model.Add(first == -1).OnlyEnforceIf(no_work)
        self._model.Add(last == -1).OnlyEnforceIf(no_work)

        span = self._model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_span")
        self._model.Add(span == last - first + 1).OnlyEnforceIf(no_work.Not())
        self._model.Add(span == 0).OnlyEnforceIf(no_work)

        gaps = self._model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_gaps")
        self._model.Add(gaps == span - sum(is_working_slots))
        self._model.Add(gaps == 0).OnlyEnforceIf(no_work)
        
        return gaps
