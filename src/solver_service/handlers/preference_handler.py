from typing import List
from ortools.sat.python import cp_model

from ..protos import problem_definition_pb2 as problem_pb
from .base_handler import BaseConstraintHandler


class PreferenceConstraintHandler(BaseConstraintHandler):
    """
    Applies soft preference constraints that affect the quality score.
    - Penalties for scheduling activities outside preferred time slots.
    - Penalties for gaps in student group schedules.
    """
    def apply(self, problem: problem_pb.ProblemDefinition) -> None:
        self._apply_time_slot_preferences(problem)
        self._apply_student_group_gap_penalties(problem)

    def _apply_time_slot_preferences(self, problem: problem_pb.ProblemDefinition) -> None:
        """Adds penalties for scheduling activities outside preferred time slots."""
        if not problem.time_preferences:
            return

        pref_map = {p.id: p for p in problem.time_preferences}

        for activity in problem.activities:
            if activity.time_preference_id in pref_map:
                preference = pref_map[activity.time_preference_id]
                absolute_preferred_slots = list(preference.preferred_slots)
                self._penalize_if_not_in_preferred_slots(
                    activity.id,
                    absolute_preferred_slots,
                    preference.penalty_per_violation
                )

    def _penalize_if_not_in_preferred_slots(self, activity_id: str, pref_slots: List[int], penalty: int) -> None:
        """Applies a penalty if an activity is not scheduled in one of its preferred slots."""
        if not pref_slots or penalty <= 0:
            return

        interval = self._modeler.activity_intervals[activity_id]
        start_var = interval.StartExpr()
        is_preferred = self._model.NewBoolVar(f"is_preferred_{activity_id}")

        allowed_assignments = [(s,) for s in pref_slots]
        self._model.AddAllowedAssignments([start_var], allowed_assignments).OnlyEnforceIf(is_preferred)
        self._model.AddForbiddenAssignments([start_var], allowed_assignments).OnlyEnforceIf(is_preferred.Not())

        self._modeler.objective_penalties.append(is_preferred.Not() * penalty)

    def _apply_student_group_gap_penalties(self, problem: problem_pb.ProblemDefinition) -> None:
        """Applies penalties for gaps in student group schedules."""
        if problem.student_gap_penalty_per_day <= 0:
            return

        for group_id, intervals in self._modeler.group_activity_map.items():
            if len(intervals) <= 1:
                continue
            
            self._penalize_daily_gaps(
                problem,
                entity_id=f"group_{group_id}",
                intervals=intervals,
                max_gaps=0,
                penalty=problem.student_gap_penalty_per_day
            )

    def _penalize_daily_gaps(self, problem: problem_pb.ProblemDefinition, entity_id: str, intervals: List, max_gaps: int, penalty: int) -> None:
        for day in range(problem.time_grid.days):
            is_working_slots = self._get_working_slots_for_day(problem, entity_id, intervals, day)
            num_gaps = self._count_gaps_in_schedule(problem, entity_id, day, is_working_slots)

            over_max_gaps = self._model.NewIntVar(0, problem.time_grid.slots_per_day, f"{entity_id}_day{day}_over_gaps")
            self._model.Add(over_max_gaps >= num_gaps - max_gaps)
            self._model.Add(over_max_gaps >= 0)

            self._modeler.objective_penalties.append(over_max_gaps * penalty)

    def _get_working_slots_for_day(self, problem: problem_pb.ProblemDefinition, entity_id: str, intervals: list, day: int) -> List[cp_model.IntVar]:
        slots_per_day = problem.time_grid.slots_per_day
        start_of_day = day * slots_per_day
        is_working_per_slot = []
        
        for slot_idx in range(slots_per_day):
            current_slot = start_of_day + slot_idx
            is_working_slot = self._model.NewBoolVar(f"{entity_id}_day{day}_slot{slot_idx}_working")
            
            literals_for_slot = []
            for interval in intervals:
                lit = self._model.NewBoolVar(f"{interval.Name()}_covers_{entity_id}_{day}_{slot_idx}")
                
                start_cond = self._model.NewBoolVar(f"{lit.Name()}_c1")
                self._model.Add(interval.StartExpr() <= current_slot).OnlyEnforceIf(start_cond)
                self._model.Add(interval.StartExpr() > current_slot).OnlyEnforceIf(start_cond.Not())

                end_cond = self._model.NewBoolVar(f"{lit.Name()}_c2")
                self._model.Add(current_slot < interval.EndExpr()).OnlyEnforceIf(end_cond)
                self._model.Add(current_slot >= interval.EndExpr()).OnlyEnforceIf(end_cond.Not())

                # CORRECCIÓN: Lógica de reificación completa para lit <=> (start_cond AND end_cond)
                # 1. lit => (start_cond AND end_cond)
                self._model.AddBoolAnd([start_cond, end_cond]).OnlyEnforceIf(lit)
                # 2. (start_cond AND end_cond) => lit  (equivale a: NOT start_cond OR NOT end_cond OR lit)
                self._model.AddBoolOr([start_cond.Not(), end_cond.Not(), lit])
                
                literals_for_slot.append(lit)
            
            if literals_for_slot:
                # is_working_slot <=> OR(literals_for_slot)
                self._model.AddBoolOr(literals_for_slot).OnlyEnforceIf(is_working_slot)
                self._model.AddImplication(is_working_slot, self._model.NewBoolVar("")).OnlyEnforceIf(
                     [l.Not() for l in literals_for_slot]
                ) # Esto es is_working_slot => OR(literals) que es lo mismo que la linea anterior, necesitamos la inversa
                # La forma correcta y completa es con AddMaxEquality
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