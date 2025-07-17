import traceback
from ortools.sat.python import cp_model

from ..constraints import fundamental, workload
from ..protos import problem_definition_pb2 as problem_pb
from ..protos import solution_pb2 as solution_pb
from ..protos import solution_pb2_grpc

from ..components.modeler import Modeler
from ..components.solution_mapper import SolutionMapper


class TimetablingService(solution_pb2_grpc.TimetablingServiceServicer):
    """
    Implements the gRPC service for solving timetabling problems.
    Acts as a "Director" that orchestrates model creation and solving.
    """

    def Solve(self, request: problem_pb.ProblemDefinition, context) -> solution_pb.Solution:
        print(f"Received Solve request for job_id: {request.job_id}")

        try:
            # 1. Instantiate the Modeler. Variables are created automatically.
            modeler = Modeler(request)

            # 2. Direct the model building by calling constraint functions in sequence.
            fundamental.apply_fundamental_constraints(modeler, request)
            workload.apply_all_workload_constraints(modeler, request)

            # 3. Finalize the model with an objective function.
            modeler.define_objective()

            # 4. Create the solver and solve the constructed model.
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = request.config.max_solve_time_seconds

            print("\n--- Solving Model ---")
            status = solver.Solve(modeler.model)
            print(f"Solver status: {solver.StatusName(status)}")

            # 5. Delegate solution mapping.
            mapper = SolutionMapper(request, modeler, solver, status)
            solution = mapper.map_solution()

            return solution

        except (ValueError, KeyError) as e:
            # Catches specific errors likely caused by bad input data.
            print(f"Error during model building, likely due to invalid problem definition: {e}")
            traceback.print_exc()
            solution = solution_pb.Solution()
            solution.job_id = request.job_id
            solution.status = solution_pb.MODEL_INVALID
            solution.message = f"Model invalid due to bad input data: {e}"
            return solution
        except Exception as e:
            # Catches all other unexpected errors.
            print(f"An unexpected internal error occurred: {e}")
            traceback.print_exc()
            solution = solution_pb.Solution()
            solution.job_id = request.job_id
            solution.status = solution_pb.MODEL_INVALID # Or a new 'INTERNAL_ERROR' status if defined
            solution.message = f"An internal server error occurred. See server logs for details."
            return solution
