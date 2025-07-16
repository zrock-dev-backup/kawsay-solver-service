from ortools.sat.python import cp_model

from ..protos import problem_definition_pb2 as problem_pb
from ..protos import solution_pb2 as solution_pb
from ..protos import solution_pb2_grpc

from ..components.modeler import Modeler
from ..components.solution_mapper import SolutionMapper


class TimetablingService(solution_pb2_grpc.TimetablingServiceServicer):
    """
    Implements the gRPC service for solving timetabling problems.
    Acts as a "Director" that calls the Modeler's methods in sequence.
    """

    def Solve(self, request: problem_pb.ProblemDefinition, context) -> solution_pb.Solution:
        print(f"Received Solve request for job_id: {request.job_id}")

        try:
            # 1. Instantiate the Modeler. Variables are created automatically.
            modeler = Modeler(request)

            # 2. Direct the Modeler to apply constraints in logical groups.
            modeler.apply_fundamental_constraints()

            # To debug an INFEASIBLE result, comment out the next line.
            modeler.apply_workload_constraints()

            # 3. Finalize the model with an objective function.
            modeler.define_objective()

            # 4. Create the solver and solve the constructed model.
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = request.config.max_solve_time_seconds

            print("\n--- Solving Model ---")
            status = solver.Solve(modeler.model)  # Pass the model from the modeler
            print(f"Solver status: {solver.StatusName(status)}")

            # 5. Delegate solution mapping.
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
