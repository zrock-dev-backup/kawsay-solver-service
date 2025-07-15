import collections
from ortools.sat.python import cp_model

import problem_definition_pb2 as problem_pb


class Modeler:
    """
    Translates a business problem definition into a mathematical CP-SAT model.
    This class is responsible for creating variables and constraints.
    """

    def __init__(self, problem: problem_pb.ProblemDefinition):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.activity_intervals = {}
        self.teacher_activity_map = collections.defaultdict(list)
        self.group_activity_map = collections.defaultdict(list)

    def build_model(self) -> cp_model.CpModel:
        """
        Builds the complete CP-SAT model with all variables and constraints.
        Returns the fully constructed model, ready to be solved.
        """
        print("--- Building Model ---")
        self._create_variables()
        self._add_conflict_constraints()
        self._add_unavailability_constraints()
        print("--- Model Built Successfully ---")
        return self.model

    def _create_variables(self):
        """Creates all decision variables for the model."""
        slots_per_day = self.problem.time_grid.slots_per_day
        total_slots = self.problem.time_grid.days * slots_per_day
        domain = (0, total_slots - 1)

        print(f"Time Grid: {self.problem.time_grid.days} days, {slots_per_day} slots/day. Total slots: {total_slots}")

        for activity in self.problem.activities:
            start_var = self.model.NewIntVar(domain[0], domain[1], f"start_{activity.id}")

            interval_var = self.model.NewIntervalVar(
                start=start_var,
                size=activity.duration_in_slots,
                end=start_var + activity.duration_in_slots,
                name=f"interval_{activity.id}"
            )
            self.activity_intervals[activity.id] = interval_var

            # Pre-populate maps for easier constraint creation later
            self.teacher_activity_map[activity.teacher_id].append(interval_var)
            for group_id in activity.student_group_ids:
                self.group_activity_map[group_id].append(interval_var)

            # Handle locked activities
            if activity.is_locked:
                locked_start_slot = activity.locked_start_time.day_index * slots_per_day + activity.locked_start_time.slot_index
                print(f"Activity '{activity.name}' is LOCKED to start at slot {locked_start_slot}")
                self.model.Add(start_var == locked_start_slot)

    def _add_conflict_constraints(self):
        """Adds NoOverlap constraints for teachers and student groups."""
        # Teacher Conflict
        for teacher_id, intervals in self.teacher_activity_map.items():
            if len(intervals) > 1:
                self.model.AddNoOverlap(intervals)
                print(f"Added NoOverlap constraint for Teacher '{teacher_id}'")

        # Student Group Conflict
        for group_id, intervals in self.group_activity_map.items():
            if len(intervals) > 1:
                self.model.AddNoOverlap(intervals)
                print(f"Added NoOverlap constraint for Student Group '{group_id}'")

    def _add_unavailability_constraints(self):
        """Adds constraints for when teachers are not available."""
        slots_per_day = self.problem.time_grid.slots_per_day
        for teacher in self.problem.teachers:
            if not teacher.unavailable_slots:
                continue

            print(f"Processing unavailability for Teacher '{teacher.name}'...")
            teacher_intervals = self.teacher_activity_map.get(teacher.id, [])
            if not teacher_intervals:
                continue

            for slot in teacher.unavailable_slots:
                start_of_forbidden_slot = slot.day_index * slots_per_day + slot.slot_index
                forbidden_interval = self.model.NewIntervalVar(
                    start=start_of_forbidden_slot,
                    size=1,
                    end=start_of_forbidden_slot + 1,
                    name=f"forbidden_{teacher.id}_{slot.day_index}_{slot.slot_index}"
                )

                for activity_interval in teacher_intervals:
                    self.model.AddNoOverlap([activity_interval, forbidden_interval])
