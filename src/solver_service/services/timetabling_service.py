import traceback
from ortools.sat.python import cp_model

from ..protos import problem_definition_pb2 as problem_pb
from ..protos import solution_pb2 as solution_pb
from ..protos import solution_pb2_grpc

from ..components.modeler import Modeler
from ..components.solution_mapper import SolutionMapper

# Explicitly import the new handlers
from ..handlers.fundamental_handler import FundamentalConstraintHandler
from ..handlers.structural_handler import StructuralConstraintHandler
from ..handlers.workload_handler import WorkloadConstraintHandler
from ..handlers.preference_handler import PreferenceConstraintHandler


class TimetablingService(solution_pb2_grpc.TimetablingServiceServicer):
    """
    Implements the gRPC service for solving timetabling problems.
    Acts as a "Director" that orchestrates model creation and solving
    by executing a pipeline of specialized handlers.
    """

    def Solve(self, request: problem_pb.ProblemDefinition, context) -> solution_pb.Solution:
        print(f"Received Solve request for job_id: {request.job_id}")

        try:
            # 1. Instantiate the Modeler. Variables are created automatically.
            modeler = Modeler(request)

            # 2. Define and execute the explicit handler pipeline.
            # The order is critical: hard constraints first, then soft/preference constraints.
            print("--- Applying Constraints via Handler Pipeline ---")
            pipeline = [
                FundamentalConstraintHandler(modeler),
                StructuralConstraintHandler(modeler),
                WorkloadConstraintHandler(modeler),
                PreferenceConstraintHandler(modeler),
            ]
            for handler in pipeline:
                print(f"Applying {handler.__class__.__name__}...")
                handler.apply(request)

            # 3. Finalize the model with an objective function from collected penalties.
            modeler.define_objective()

            # 4. Create the solver and solve the constructed model.
            solver = cp_model.CpSolver()
            if request.config.max_solve_time_seconds > 0:
                solver.parameters.max_time_in_seconds = request.config.max_solve_time_seconds

            print("\n--- Solving Model ---")
            status = solver.Solve(modeler.model)
            print(f"Solver status: {solver.StatusName(status)}")

            # 5. Delegate solution mapping.
            mapper = SolutionMapper(request, modeler, solver, status)
            solution = mapper.map_solution()

            return solution

        except (ValueError, KeyError) as e:
            print(f"Error during model building, likely due to invalid problem definition: {e}")
            traceback.print_exc()
            solution = solution_pb.Solution()
            solution.job_id = request.job_id
            solution.status = solution_pb.MODEL_INVALID
            solution.message = f"Model invalid due to bad input data: {e}"
            return solution
        except Exception as e:
            print(f"An unexpected internal error occurred: {e}")
            traceback.print_exc()
            solution = solution_pb.Solution()
            solution.job_id = request.job_id
            solution.status = solution_pb.MODEL_INVALID
            solution.message = f"An internal server error occurred. See server logs for details."
            return solution
