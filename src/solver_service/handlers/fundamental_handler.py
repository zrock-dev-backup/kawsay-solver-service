from ..protos import problem_definition_pb2 as problem_pb
from .base_handler import BaseConstraintHandler


class FundamentalConstraintHandler(BaseConstraintHandler):
    """
    Applies non-negotiable hard constraints that define a valid timetable.
    - Resource conflicts (teacher, student group)
    - Teacher unavailability
    - System-wide breaks
    """
    def apply(self, problem: problem_pb.ProblemDefinition) -> None:
        self._enforce_resource_conflicts(problem)
        self._enforce_teacher_unavailability(problem)
        self._enforce_system_breaks(problem)
        self._enforce_day_boundaries(problem)

    def _enforce_resource_conflicts(self, problem: problem_pb.ProblemDefinition) -> None:
        """A resource (teacher or group) cannot be in two places at once."""
        for teacher_id, intervals in self._modeler.teacher_activity_map.items():
            if len(intervals) > 1:
                self._model.AddNoOverlap(intervals)

        for group_id, intervals in self._modeler.group_activity_map.items():
            if len(intervals) > 1:
                self._model.AddNoOverlap(intervals)

    def _enforce_teacher_unavailability(self, problem: problem_pb.ProblemDefinition) -> None:
        """A teacher cannot be scheduled during their unavailable slots."""
        slots_per_day = problem.time_grid.slots_per_day
        for teacher in problem.teachers:
            teacher_intervals = self._modeler.teacher_activity_map.get(teacher.id)
            if not teacher.unavailable_slots or not teacher_intervals:
                continue

            all_intervals = teacher_intervals[:]
            for slot in teacher.unavailable_slots:
                start = slot.day_index * slots_per_day + slot.slot_index
                forbidden = self._model.NewFixedSizeIntervalVar(
                    start, 1, f"forbidden_{teacher.id}_{slot.day_index}_{slot.slot_index}"
                )
                all_intervals.append(forbidden)

            if len(all_intervals) > 1:
                self._model.AddNoOverlap(all_intervals)

    def _enforce_system_breaks(self, problem: problem_pb.ProblemDefinition) -> None:
        """No activities can be scheduled during system-wide breaks (holidays)."""
        if not problem.system_breaks:
            return

        break_intervals = []
        slots_per_day = problem.time_grid.slots_per_day
        for break_period in problem.system_breaks:
            start = break_period.start_day * slots_per_day
            duration = (break_period.end_day - break_period.start_day + 1) * slots_per_day
            break_intervals.append(
                self._model.NewFixedSizeIntervalVar(start, duration, f"break_{break_period.id}")
            )

        # Every activity must not overlap with any break period.
        for activity_interval in self._modeler.activity_intervals.values():
            self._model.AddNoOverlap(break_intervals + [activity_interval])

    def _enforce_day_boundaries(self, problem: problem_pb.ProblemDefinition) -> None:
        """An activity cannot cross from one day to the next."""
        slots_per_day = problem.time_grid.slots_per_day
        if slots_per_day <= 0:
            return

        for activity_id, interval in self._modeler.activity_intervals.items():
            activity = self._modeler.id_to_activity_map[activity_id]
            if activity.duration_in_slots > slots_per_day:
                continue  # Constraint is moot for activities longer than a day

            start_var = interval.StartExpr()
            start_day = self._model.NewIntVar(0, problem.time_grid.days - 1, f"start_day_{activity_id}")
            end_day = self._model.NewIntVar(0, problem.time_grid.days - 1, f"end_day_{activity_id}")

            self._model.AddDivisionEquality(start_day, start_var, slots_per_day)
            self._model.AddDivisionEquality(end_day, interval.EndExpr() - 1, slots_per_day)
            self._model.Add(start_day == end_day)
