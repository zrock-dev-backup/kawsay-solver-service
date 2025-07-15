from ortools.sat.python import cp_model

import problem_definition_pb2 as problem_pb
import solution_pb2 as solution_pb
from .modeler import Modeler

class SolutionMapper:
    """
    Translates the raw output of the CpSolver into the final Solution protobuf message.
    """
    def __init__(self, problem: problem_pb.ProblemDefinition, modeler: Modeler, solver: cp_model.CpSolver, status: int):
        self.problem = problem
        self.modeler = modeler
        self.solver = solver
        self.status = status

    def map_solution(self) -> solution_pb.Solution:
        """Constructs the Solution message based on the solver's status and results."""
        solution = solution_pb.Solution()
        solution.job_id = self.problem.job_id
        solution.status = self._get_solution_status()
        
        if self.status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
            solution.message = "A valid schedule was found."
            self._populate_scheduled_activities(solution)
        elif self.status == cp_model.INFEASIBLE:
            solution.message = "The problem is infeasible. No solution exists under the given constraints."
        else:
            solution.message = "An error occurred during solving."
            
        return solution

    def _get_solution_status(self) -> solution_pb.SolverStatus:
        """Maps the OR-Tools status enum to our custom protobuf enum."""
        status_map = {
            cp_model.OPTIMAL: solution_pb.OPTIMAL,
            cp_model.FEASIBLE: solution_pb.FEASIBLE,
            cp_model.INFEASIBLE: solution_pb.INFEASIBLE,
            cp_model.MODEL_INVALID: solution_pb.MODEL_INVALID,
        }
        return status_map.get(self.status, solution_pb.UNKNOWN)

    def _populate_scheduled_activities(self, solution: solution_pb.Solution):
        """Fills in the scheduled activities list from the solver's variable values."""
        slots_per_day = self.problem.time_grid.slots_per_day
        for activity in self.problem.activities:
            interval_var = self.modeler.activity_intervals[activity.id]
            start_slot_val = self.solver.Value(interval_var.StartExpr())
            
            scheduled_activity = solution.scheduled_activities.add()
            scheduled_activity.activity_id = activity.id
            scheduled_activity.start_time.day_index = start_slot_val // slots_per_day
            scheduled_activity.start_time.slot_index = start_slot_val % slots_per_day
