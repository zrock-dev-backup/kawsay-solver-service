from ortools.sat.python import cp_model

import problem_definition_pb2 as problem_pb
import solution_pb2 as solution_pb
import solution_pb2_grpc

from components.modeler import Modeler
from components.solution_mapper import SolutionMapper

class TimetablingService(solution_pb2_grpc.TimetablingServiceServicer):
    """
    Implements the gRPC service for solving timetabling problems.
    """
    def Solve(self, request: problem_pb.ProblemDefinition, context) -> solution_pb.Solution:
        """
        Handles a single 'Solve' request.
        Orchestrates the model building, solving, and solution mapping.
        """
        print(f"Received Solve request for job_id: {request.job_id}")
        
        try:
            # 1. Delegate model building
            modeler = Modeler(request)
            model = modeler.build_model()
            
            # 2. Create the solver and solve
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = request.config.max_solve_time_seconds
            
            print("\n--- Solving Model ---")
            status = solver.Solve(model)
            print(f"Solver status: {solver.StatusName(status)}")
            
            # 3. Delegate solution mapping
            mapper = SolutionMapper(request, modeler, solver, status)
            solution = mapper.map_solution()
            
            return solution
            
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            # Create an error response
            solution = solution_pb.Solution()
            solution.job_id = request.job_id
            solution.status = solution_pb.MODEL_INVALID
            solution.message = f"An internal error occurred in the solver service: {e}"
            return solution
