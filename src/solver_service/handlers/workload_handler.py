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
        slots_per_day = problem.time_grid.slots_per_day
        
        for day in range(problem.time_grid.days):
            is_active_on_day = self._model.NewBoolVar(f"t{teacher_id}_active_on_day_{day}")
            
            literals_for_day = []
            for interval in intervals:
                activity_day = self._model.NewIntVar(0, problem.time_grid.days - 1, f"{interval.Name()}_day")
                self._model.AddDivisionEquality(activity_day, interval.StartExpr(), slots_per_day)
                
                lit = self._model.NewBoolVar(f"{interval.Name()}_on_day_{day}")
                self._model.Add(activity_day == day).OnlyEnforceIf(lit)
                self._model.Add(activity_day != day).OnlyEnforceIf(lit.Not())
                literals_for_day.append(lit)
            
            if not literals_for_day:
                self._model.Add(is_active_on_day == 0)
            else:
                self._model.AddMaxEquality(is_active_on_day, literals_for_day)
            
            days_working_flags.append(is_active_on_day)
        
        self._model.Add(sum(days_working_flags) <= max_days)

    def _penalize_daily_gaps(self, problem: problem_pb.ProblemDefinition, entity_id: str, intervals: List, max_gaps: int, penalty: int) -> None:
        if len(intervals) <= 1:
            return

        for day in range(problem.time_grid.days):
            is_working_slots = self._get_working_slots_for_day(problem, entity_id, intervals, day)
            num_gaps = self._count_gaps_in_schedule(problem, entity_id, day, is_working_slots)

            over_max_gaps = self._model.NewIntVar(0, problem.time_grid.slots_per_day, f"{entity_id}_day{day}_over_gaps")
            self._model.Add(over_max_gaps >= num_gaps - max_gaps)
            self._model.Add(over_max_gaps >= 0)

            self._modeler.objective_penalties.append(over_max_gaps * penalty)

    def _is_interval_on_day(self, interval: cp_model.IntervalVar, day: int, slots_per_day: int, prefix: str) -> cp_model.IntVar:
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
        self._model.AddBoolOr([lit1.Not(), lit2.Not()]).OnlyEnforceIf(is_on_day.Not())
        return is_on_day
    
    def _get_working_slots_for_day(self, problem: problem_pb.ProblemDefinition, entity_id: str, intervals: list, day: int) -> List[cp_model.IntVar]:
        slots_per_day = problem.time_grid.slots_per_day
        start_of_day = day * slots_per_day
        is_working_per_slot = []
        
        for slot_idx in range(slots_per_day):
            current_slot = start_of_day + slot_idx
            is_working_slot = self._model.NewBoolVar(f"{entity_id}_day{day}_slot{slot_idx}_working")
            
            literals_for_slot = []
            for interval in intervals:
                lit = self._model.NewBoolVar(f"{interval.Name()}_covers_{day}_{slot_idx}")
                
                start_cond = self._model.NewBoolVar(f"{lit.Name()}_c1")
                self._model.Add(interval.StartExpr() <= current_slot).OnlyEnforceIf(start_cond)
                self._model.Add(interval.StartExpr() > current_slot).OnlyEnforceIf(start_cond.Not())

                end_cond = self._model.NewBoolVar(f"{lit.Name()}_c2")
                self._model.Add(current_slot < interval.EndExpr()).OnlyEnforceIf(end_cond)
                self._model.Add(current_slot >= interval.EndExpr()).OnlyEnforceIf(end_cond.Not())

                # CORRECCIÓN: Lógica de reificación completa para lit <=> (start_cond AND end_cond)
                # 1. lit => (start_cond AND end_cond)
                self._model.AddBoolAnd([start_cond, end_cond]).OnlyEnforceIf(lit)
                # 2. (start_cond AND end_cond) => lit (equivale a: NOT start_cond OR NOT end_cond OR lit)
                self._model.AddBoolOr([start_cond.Not(), end_cond.Not(), lit])

                literals_for_slot.append(lit)
            
            if literals_for_slot:
                 # La forma más robusta y correcta de expresar "is_working_slot <=> OR(literals_for_slot)"
                self._model.AddMaxEquality(is_working_slot, literals_for_slot)
            else:
                self._model.Add(is_working_slot == 0)
            is_working_per_slot.append(is_working_slot)
        
        return is_working_per_slot
    
    def _count_gaps_in_schedule(self, problem: problem_pb.ProblemDefinition, entity_id: str, day: int, is_working_slots: List[cp_model.IntVar]) -> cp_model.IntVar:
        slots_per_day = len(is_working_slots)
    
        slot_indices = list(range(slots_per_day))

        first = self._model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_first")
        last = self._model.NewIntVar(-1, slots_per_day -1, f"{entity_id}_day{day}_last")
        
        first_options = []
        last_options = []
        for i in range(slots_per_day):
            var_f = self._model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_first_opt_{i}")
            self._model.Add(var_f == slot_indices[i]).OnlyEnforceIf(is_working_slots[i])
            self._model.Add(var_f == slots_per_day).OnlyEnforceIf(is_working_slots[i].Not())
            first_options.append(var_f)
            
            var_l = self._model.NewIntVar(-1, slots_per_day - 1, f"{entity_id}_day{day}_last_opt_{i}")
            self._model.Add(var_l == slot_indices[i]).OnlyEnforceIf(is_working_slots[i])
            self._model.Add(var_l == -1).OnlyEnforceIf(is_working_slots[i].Not())
            last_options.append(var_l)
            
        self._model.AddMinEquality(first, first_options)
        self._model.AddMaxEquality(last, last_options)
        
        no_work_sentinel = self._model.NewBoolVar(f"{entity_id}_day{day}_no_work")
        self._model.Add(sum(is_working_slots) == 0).OnlyEnforceIf(no_work_sentinel)
        self._model.Add(sum(is_working_slots) > 0).OnlyEnforceIf(no_work_sentinel.Not())
        
        span = self._model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_span")
        self._model.Add(span == last - first + 1).OnlyEnforceIf(no_work_sentinel.Not())
        self._model.Add(span == 0).OnlyEnforceIf(no_work_sentinel)

        gaps = self._model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_gaps")
        self._model.Add(gaps == span - sum(is_working_slots))
        
        return gaps