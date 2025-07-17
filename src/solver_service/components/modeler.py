import collections
from ortools.sat.python import cp_model
from ..protos import problem_definition_pb2 as problem_pb

class Modeler:
    """
    Builds the CP-SAT model's core variables and provides mappings for constraints.
    Constraint logic itself is delegated to dedicated modules.
    """
    def __init__(self, problem: problem_pb.ProblemDefinition):
        self.problem = problem
        self.model = cp_model.CpModel()
        
        # Core data structures for the model
        self.activity_intervals = {}
        self.objective_penalties = []
        
        # Maps for quick lookups by constraint modules
        self.teacher_activity_map = collections.defaultdict(list)
        self.group_activity_map = collections.defaultdict(list)
        self.interval_to_activity_map = {}
        self.id_to_activity_map = {} # Added: Required by constraint modules
        
        self._create_variables()

    def _create_variables(self):
        """(Private) Sets up the fundamental decision variables for the model."""
        print("--- Building Model: Creating Variables ---")
        slots_per_day = self.problem.time_grid.slots_per_day
        total_slots = self.problem.time_grid.days * slots_per_day
        domain = (0, total_slots - 1)

        for activity in self.problem.activities:
            self.id_to_activity_map[activity.id] = activity # Populate the new map

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

    def define_objective(self):
        """(Public) Sets the final objective function from collected penalties."""
        if self.objective_penalties:
            print("--- Defining Objective Function ---")
            self.model.Minimize(sum(self.objective_penalties))
