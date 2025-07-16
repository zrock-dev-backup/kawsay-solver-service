import collections
from ortools.sat.python import cp_model
from ..protos import problem_definition_pb2 as problem_pb

class Modeler:
    """
    Builds the CP-SAT model by applying groups of constraints in a sequence
    directed by the main service. This class is cohesive, keeping all modeling
    logic in one place, but exposes a clear API for debugging and control.
    """
    def __init__(self, problem: problem_pb.ProblemDefinition):
        self.problem = problem
        self.model = cp_model.CpModel()
        self.activity_intervals = {}
        self.teacher_activity_map = collections.defaultdict(list)
        self.group_activity_map = collections.defaultdict(list)
        self.interval_to_activity_map = {}
        self.objective_penalties = []
        
        self._create_variables()

    def _create_variables(self):
        """(Private) Sets up the fundamental decision variables for the model."""
        print("--- Building Model: Creating Variables ---")
        slots_per_day = self.problem.time_grid.slots_per_day
        total_slots = self.problem.time_grid.days * slots_per_day
        domain = (0, total_slots - 1)

        for activity in self.problem.activities:
            start_var = self.model.NewIntVar(domain[0], domain[1], f"start_{activity.id}")
            interval_var = self.model.NewIntervalVar(
                start=start_var,
                size=activity.duration_in_slots,
                end=start_var + activity.duration_in_slots,
                name=f"interval_{activity.id}"
            )
            self.activity_intervals[activity.id] = interval_var
            self.interval_to_activity_map[interval_var] = activity
            self.teacher_activity_map[activity.teacher_id].append(interval_var)
            for group_id in activity.student_group_ids:
                self.group_activity_map[group_id].append(interval_var)

            if activity.is_locked:
                locked_start_slot = activity.locked_start_time.day_index * slots_per_day + activity.locked_start_time.slot_index
                self.model.Add(start_var == locked_start_slot)

    def apply_fundamental_constraints(self):
        """(Public) Applies all non-negotiable hard constraints."""
        print("  - Applying Fundamental Constraints (Conflicts, Unavailability)...")
        # Teacher Conflict
        for intervals in self.teacher_activity_map.values():
            if len(intervals) > 1:
                self.model.AddNoOverlap(intervals)
        # Student Group Conflict
        for intervals in self.group_activity_map.values():
            if len(intervals) > 1:
                self.model.AddNoOverlap(intervals)
        # Teacher Unavailability
        slots_per_day = self.problem.time_grid.slots_per_day
        for teacher in self.problem.teachers:
            if not teacher.unavailable_slots: continue
            teacher_intervals = self.teacher_activity_map.get(teacher.id, [])
            if not teacher_intervals: continue
            for slot in teacher.unavailable_slots:
                start_of_forbidden_slot = slot.day_index * slots_per_day + slot.slot_index
                forbidden_interval = self.model.NewIntervalVar(start_of_forbidden_slot, 1, start_of_forbidden_slot + 1, f"forbidden_{teacher.id}_{slot.day_index}_{slot.slot_index}")
                for activity_interval in teacher_intervals:
                    self.model.AddNoOverlap([activity_interval, forbidden_interval])

    def apply_workload_constraints(self):
        """(Public) Applies all workload and quality-of-life constraints."""
        print("  - Applying Workload & Quality Constraints...")
        slots_per_day = self.problem.time_grid.slots_per_day

        for constraint in self.problem.workload_constraints:
            teacher_id = constraint.teacher_id
            teacher_intervals = self.teacher_activity_map.get(teacher_id, [])
            if not teacher_intervals: continue

            # --- Max Hours Per Day (Hard) ---
            if constraint.max_hours_per_day > 0:
                # Loop through each day to apply the constraint independently per day.
                for day in range(self.problem.time_grid.days):
                    # Create a FRESH list of demands for THIS day only.
                    demands_for_this_day = []
                    for interval in teacher_intervals:
                        activity = self.interval_to_activity_map[interval]
                        duration = activity.duration_in_slots # This is a CONSTANT.

                        # is_on_day is a boolean VARIABLE that is true if the activity starts on this day.
                        is_on_day = self.model.NewBoolVar(f"{activity.id}_on_day_{day}")

                        start_of_day = day * slots_per_day
                        end_of_day = start_of_day + slots_per_day

                        # Correctly define the "iff" relationship:
                        # is_on_day is true <=> interval starts within the day's bounds.
                        self.model.Add(interval.StartExpr() >= start_of_day).OnlyEnforceIf(is_on_day)
                        self.model.Add(interval.StartExpr() < end_of_day).OnlyEnforceIf(is_on_day)

                        # Add the reverse implication to strengthen the model.
                        # If the interval starts outside this day, is_on_day must be false.
                        lit_before = self.model.NewBoolVar('')
                        self.model.Add(interval.StartExpr() < start_of_day).OnlyEnforceIf(lit_before)
                        lit_after = self.model.NewBoolVar('')
                        self.model.Add(interval.StartExpr() >= end_of_day).OnlyEnforceIf(lit_after)
                        self.model.AddImplication(lit_before, is_on_day.Not())
                        self.model.AddImplication(lit_after, is_on_day.Not())

                        # The demand is a LINEAR expression: constant * boolean_variable.
                        demands_for_this_day.append(duration * is_on_day)

                    # Apply the constraint using the demands FOR THIS DAY ONLY.
                    self.model.Add(sum(demands_for_this_day) <= constraint.max_hours_per_day)

            # --- Max Gaps Per Day (Soft) ---
            # This logic was correct.
            if constraint.max_gaps_per_day >= 0 and constraint.penalty_per_gap > 0:
                for day in range(self.problem.time_grid.days):
                    is_working = [self.model.NewBoolVar(f"{teacher_id}_day{day}_slot{s}_working") for s in range(slots_per_day)]
                    for s in range(slots_per_day):
                        slot_start = day * slots_per_day + s
                        literals = []
                        for interval in teacher_intervals:
                            lit = self.model.NewBoolVar('')
                            self.model.Add(interval.StartExpr() <= slot_start).OnlyEnforceIf(lit)
                            self.model.Add(interval.EndExpr() > slot_start).OnlyEnforceIf(lit)
                            self.model.AddImplication(lit, is_working[s])
                            literals.append(lit)
                        self.model.AddBoolOr(literals).OnlyEnforceIf(is_working[s])

                    gaps_in_day = []
                    for s in range(1, slots_per_day):
                        is_gap = self.model.NewBoolVar(f"{teacher_id}_day{day}_slot{s}_is_gap")
                        self.model.AddBoolAnd([is_working[s-1], is_working[s].Not()]).OnlyEnforceIf(is_gap)
                        gaps_in_day.append(is_gap)

                    num_gaps = self.model.NewIntVar(0, slots_per_day, f"{teacher_id}_day{day}_num_gaps")
                    self.model.Add(num_gaps == sum(gaps_in_day))
                    over_max_gaps = self.model.NewIntVar(0, slots_per_day, f"{teacher_id}_day{day}_over_gaps")
                    self.model.Add(over_max_gaps >= num_gaps - constraint.max_gaps_per_day)
                    self.objective_penalties.append(over_max_gaps * constraint.penalty_per_gap)


    def define_objective(self):
        """(Public) Sets the final objective function from collected penalties."""
        if self.objective_penalties:
            print("--- Defining Objective Function ---")
            self.model.Minimize(sum(self.objective_penalties))
