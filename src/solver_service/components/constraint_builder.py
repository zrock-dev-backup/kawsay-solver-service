from typing import List
from ortools.sat.python import cp_model

from .modeler import Modeler
from ..protos import problem_definition_pb2 as problem_pb


class ConstraintBuilder:
    """
    Provides a high-level, cohesive API for adding constraints to the model.

    This class acts as a Gateway that insulates business logic from the raw
    ortools API. It is the single point of contact for all constraint creation.
    The logic from the former 'constraint_utils' module has been absorbed into
    this class as private methods to ensure strong cohesion.
    """

    def __init__(self, modeler: Modeler):
        self._modeler = modeler
        self._model = modeler.model
        self._problem = modeler.problem

    # =========================================================================
    # Public API - Fundamental Constraints
    # =========================================================================

    def enforce_teacher_conflict(self, teacher_id: str):
        """A teacher cannot be assigned to more than one activity at the same time."""
        intervals = self._modeler.teacher_activity_map.get(teacher_id, [])
        if len(intervals) > 1:
            self._model.AddNoOverlap(intervals)

    def enforce_student_group_conflict(self, group_id: str):
        """A student group cannot attend more than one activity at the same time."""
        intervals = self._modeler.group_activity_map.get(group_id, [])
        if len(intervals) > 1:
            self._model.AddNoOverlap(intervals)

    def enforce_teacher_unavailability(self, teacher_id: str):
        """A teacher cannot be scheduled during their pre-defined unavailable slots."""
        teacher = self._modeler.id_to_teacher_map.get(teacher_id)
        if not teacher or not teacher.unavailable_slots:
            return
        self._apply_teacher_unavailability(teacher)

    def enforce_system_breaks(self):
        """No activities can be scheduled during system-wide breaks (holidays)."""
        break_intervals = []
        slots_per_day = self._problem.time_grid.slots_per_day
        for break_period in self._problem.system_breaks:
            start = break_period.start_day * slots_per_day
            duration = (break_period.end_day - break_period.start_day + 1) * slots_per_day
            break_intervals.append(
                self._model.NewFixedSizeIntervalVar(start, duration, f"break_{break_period.id}")
            )
        if not break_intervals:
            return
        for activity_interval in self._modeler.activity_intervals.values():
            self._model.AddNoOverlap(break_intervals + [activity_interval])

    # =========================================================================
    # Public API - Structural Constraints
    # =========================================================================

    def enforce_day_boundaries(self, activity_id: str):
        """An activity cannot cross from one day to the next."""
        slots_per_day = self._problem.time_grid.slots_per_day
        if slots_per_day <= 0: return

        interval = self._modeler.activity_intervals[activity_id]
        activity = self._modeler.id_to_activity_map[activity_id]
        if activity.duration_in_slots > slots_per_day:
            return  # This constraint is moot for activities longer than a day

        start_var = interval.StartExpr()
        start_day = self._model.NewIntVar(0, self._problem.time_grid.days - 1, f"start_day_{activity_id}")
        end_day = self._model.NewIntVar(0, self._problem.time_grid.days - 1, f"end_day_{activity_id}")

        self._model.AddDivisionEquality(start_day, start_var, slots_per_day)
        self._model.AddDivisionEquality(end_day, interval.EndExpr() - 1, slots_per_day)
        self._model.Add(start_day == end_day)

    def enforce_activity_ordering(self, before_id: str, after_id: str):
        """Activity A must end before or when Activity B begins."""
        before_interval = self._modeler.activity_intervals[before_id]
        after_interval = self._modeler.activity_intervals[after_id]
        self._model.Add(before_interval.EndExpr() <= after_interval.StartExpr())

    def enforce_consecutive_activities(self, first_id: str, second_id: str):
        """Activity A must be immediately followed by Activity B."""
        first_interval = self._modeler.activity_intervals[first_id]
        second_interval = self._modeler.activity_intervals[second_id]
        self._model.Add(first_interval.EndExpr() == second_interval.StartExpr())

    def enforce_min_days_between(self, act1_id: str, act2_id: str, min_days: int):
        """A minimum number of full days must pass between two activities."""
        slots_per_day = self._problem.time_grid.slots_per_day
        if slots_per_day <= 0: return

        act1_day = self._get_day_of_activity(act1_id)
        act2_day = self._get_day_of_activity(act2_id)

        day_diff = self._model.NewIntVar(0, self._problem.time_grid.days, f"day_diff_{act1_id}_{act2_id}")
        self._model.AddAbsEquality(day_diff, act1_day - act2_day)
        self._model.Add(day_diff >= min_days)

    # =========================================================================
    # Public API - Workload & Preference Constraints
    # =========================================================================

    def enforce_max_hours_per_day(self, teacher_id: str, max_hours: int):
        """A teacher's total scheduled hours on any given day cannot exceed a maximum."""
        intervals = self._modeler.teacher_activity_map.get(teacher_id, [])
        if not intervals: return

        for day in range(self._problem.time_grid.days):
            daily_load = self._get_daily_load(intervals, day, f"t{teacher_id}_maxhrs")
            self._model.Add(daily_load <= max_hours)

    def enforce_max_hours_per_week(self, teacher_id: str, max_hours: int):
        """A teacher's total scheduled hours must not exceed their contractual limit."""
        intervals = self._modeler.teacher_activity_map.get(teacher_id, [])
        if not intervals: return
        total_duration = sum(self._modeler.interval_to_activity_map[i].duration_in_slots for i in intervals)
        self._model.Add(total_duration <= max_hours)

    def enforce_max_days_per_week(self, teacher_id: str, max_days: int):
        """A teacher cannot be forced to work more than a maximum number of days."""
        intervals = self._modeler.teacher_activity_map.get(teacher_id, [])
        if not intervals: return

        days_working_flags = []
        for day in range(self._problem.time_grid.days):
            is_active_on_day = self._is_entity_active_on_day(intervals, day, f"t{teacher_id}_maxdays")
            days_working_flags.append(is_active_on_day)

        if days_working_flags:
            self._model.Add(sum(days_working_flags) <= max_days)

    def penalize_daily_gaps(self, entity_id: str, intervals: List, max_gaps: int, penalty: int):
        """Applies a penalty for each gap over a maximum for an entity on a given day."""
        if len(intervals) <= 1 or penalty <= 0: return

        for day in range(self._problem.time_grid.days):
            is_working_slots = self._get_working_slots_for_day(entity_id, intervals, day)
            num_gaps = self._count_gaps_in_schedule(entity_id, day, is_working_slots)

            over_max_gaps = self._model.NewIntVar(0, self._problem.time_grid.slots_per_day,
                                                  f"{entity_id}_day{day}_over_gaps")
            self._model.Add(over_max_gaps >= num_gaps - max_gaps)
            self._modeler.objective_penalties.append(over_max_gaps * penalty)

    def penalize_if_not_in_preferred_slots(self, activity_id: str, pref_slots: List[int], penalty: int):
        """Applies a penalty if an activity is not scheduled in one of its preferred slots."""
        if not pref_slots or penalty <= 0: return

        interval = self._modeler.activity_intervals[activity_id]
        start_var = interval.StartExpr()
        is_preferred = self._model.NewBoolVar(f"is_preferred_{activity_id}")

        self._model.Add(start_var.In(pref_slots)).OnlyEnforceIf(is_preferred)
        self._model.Add(start_var.NotIn(pref_slots)).OnlyEnforceIf(is_preferred.Not())

        self._modeler.objective_penalties.append(is_preferred.Not() * penalty)

    # =========================================================================
    # Private Helper Methods (Formerly constraint_utils.py)
    # =========================================================================

    def _apply_teacher_unavailability(self, teacher: problem_pb.Teacher):
        slots_per_day = self._problem.time_grid.slots_per_day
        teacher_intervals = self._modeler.teacher_activity_map.get(teacher.id, [])
        if not teacher_intervals: return

        all_intervals = teacher_intervals[:]
        for slot in teacher.unavailable_slots:
            start = slot.day_index * slots_per_day + slot.slot_index
            forbidden = self._model.NewFixedSizeIntervalVar(start, 1,
                                                            f"forbidden_{teacher.id}_{slot.day_index}_{slot.slot_index}")
            all_intervals.append(forbidden)

        if len(all_intervals) > 1:
            self._model.AddNoOverlap(all_intervals)

    def _get_day_of_activity(self, activity_id: str) -> cp_model.IntVar:
        slots_per_day = self._problem.time_grid.slots_per_day
        start_var = self._modeler.activity_intervals[activity_id].StartExpr()
        day_var = self._model.NewIntVar(0, self._problem.time_grid.days - 1, f"day_{activity_id}")
        self._model.AddDivisionEquality(day_var, start_var, slots_per_day)
        return day_var

    def _get_daily_load(self, intervals: list, day: int, prefix: str) -> cp_model.IntVar:
        is_on_day_literals = self._get_day_active_literals(intervals, day, prefix)
        daily_workload = []
        for i, interval in enumerate(intervals):
            activity = self._modeler.interval_to_activity_map[interval]
            daily_workload.append(activity.duration_in_slots * is_on_day_literals[i])
        return sum(daily_workload)

    def _is_entity_active_on_day(self, intervals: list, day: int, prefix: str) -> cp_model.IntVar:
        is_active_on_day = self._model.NewBoolVar(f"{prefix}_active_day_{day}")
        day_activity_literals = self._get_day_active_literals(intervals, day, prefix)

        if day_activity_literals:
            self._model.AddBoolOr(day_activity_literals).OnlyEnforceIf(is_active_on_day)
            self._model.Add(is_active_on_day == 0).OnlyEnforceIf([lit.Not() for lit in day_activity_literals])
        else:
            self._model.Add(is_active_on_day == 0)
        return is_active_on_day

    def _get_day_active_literals(self, intervals: list, day: int, prefix: str) -> List[cp_model.IntVar]:
        slots_per_day = self._problem.time_grid.slots_per_day
        start_of_day = day * slots_per_day
        end_of_day = start_of_day + slots_per_day
        literals = []
        for i, interval in enumerate(intervals):
            is_on_day = self._model.NewBoolVar(f"{prefix}_on_day_{day}_interval_{i}")
            start_var = interval.StartExpr()
            lit1 = self._model.NewBoolVar(f"{is_on_day.Name()}_ge")
            self._model.Add(start_var >= start_of_day).OnlyEnforceIf(lit1)
            self._model.Add(start_var < start_of_day).OnlyEnforceIf(lit1.Not())
            lit2 = self._model.NewBoolVar(f"{is_on_day.Name()}_lt")
            self._model.Add(start_var < end_of_day).OnlyEnforceIf(lit2)
            self._model.Add(start_var >= end_of_day).OnlyEnforceIf(lit2.Not())
            self._model.AddBoolAnd([lit1, lit2]).OnlyEnforceIf(is_on_day)
            self._model.AddImplication(lit1.Not(), is_on_day.Not())
            self._model.AddImplication(lit2.Not(), is_on_day.Not())
            literals.append(is_on_day)
        return literals

    def _get_working_slots_for_day(self, entity_id: str, intervals: list, day: int) -> List[cp_model.IntVar]:
        slots_per_day = self._problem.time_grid.slots_per_day
        start_of_day = day * slots_per_day
        is_working_per_slot = []
        for slot_idx in range(slots_per_day):
            current_slot = start_of_day + slot_idx
            is_working_slot = self._model.NewBoolVar(f"{entity_id}_day{day}_slot{slot_idx}_working")
            is_working_per_slot.append(is_working_slot)
            literals_for_slot = []
            for interval in intervals:
                lit = self._model.NewBoolVar(f"{interval.Name()}_covers_{day}_{slot_idx}")
                start_cond = self._model.NewBoolVar(f"{lit.Name()}_start_cond")
                self._model.Add(interval.StartExpr() <= current_slot).OnlyEnforceIf(start_cond)
                self._model.Add(interval.StartExpr() > current_slot).OnlyEnforceIf(start_cond.Not())
                end_cond = self._model.NewBoolVar(f"{lit.Name()}_end_cond")
                self._model.Add(current_slot < interval.EndExpr()).OnlyEnforceIf(end_cond)
                self._model.Add(current_slot >= interval.EndExpr()).OnlyEnforceIf(end_cond.Not())
                self._model.AddBoolAnd([start_cond, end_cond]).OnlyEnforceIf(lit)
                literals_for_slot.append(lit)
            if literals_for_slot:
                self._model.AddBoolOr(literals_for_slot).OnlyEnforceIf(is_working_slot)
                self._model.Add(is_working_slot == 0).OnlyEnforceIf([l.Not() for l in literals_for_slot])
            else:
                self._model.Add(is_working_slot == 0)
        return is_working_per_slot

    def _count_gaps_in_schedule(self, entity_id: str, day: int,
                                is_working_slots: List[cp_model.IntVar]) -> cp_model.IntVar:
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
