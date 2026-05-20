import os
import traceback
from opentelemetry import trace
from ortools.sat.python import cp_model
from google.protobuf.json_format import MessageToJson

from ..protos import problem_definition_pb2 as problem_pb
from ..protos import solution_pb2 as solution_pb
from ..protos import solution_pb2_grpc

from ..components.modeler import Modeler
from ..components.solution_mapper import SolutionMapper

from ..handlers.fundamental_handler import FundamentalConstraintHandler
from ..handlers.structural_handler import StructuralConstraintHandler
from ..handlers.workload_handler import WorkloadConstraintHandler
from ..handlers.preference_handler import PreferenceConstraintHandler

tracer = trace.get_tracer("timetabling.solver")

# Feature flag to prevent accidental massive APM bills in production
VERBOSE_TELEMETRY = os.getenv("VERBOSE_TELEMETRY", "true").lower() == "true"

# In SolverGrpcClient.cs, you were using Name = $"Teacher {tId}". You should now update the solver input to pass the ExternalTeacherId directly, ensuring the Solver engine uses the same identity as the Teacher API.

class TimetablingService(solution_pb2_grpc.TimetablingServiceServicer):

    def Solve(self, request: problem_pb.ProblemDefinition, context) -> solution_pb.Solution:
        with tracer.start_as_current_span("Orchestrate.TimetableSolve") as span:
            span.set_attribute("timetabling.job.id", request.job_id)
            
            # --- 1. INDEXABLE ATTRIBUTES (Searchable in APM) ---
            span.set_attribute("timetabling.input.days", request.time_grid.days)
            span.set_attribute("timetabling.input.slots_per_day", request.time_grid.slots_per_day)
            
            # Extract arrays of IDs for indexing (helps find specific entity failures)
            span.set_attribute("timetabling.entities.teachers", [t.id for t in request.teachers])
            span.set_attribute("timetabling.entities.groups", [g.id for g in request.student_groups])
            span.set_attribute("timetabling.entities.activities", [a.id for a in request.activities])

            # --- 2. VERBOSE PAYLOAD LOGGING (Events) ---
            if VERBOSE_TELEMETRY:
                # Convert the incoming protobuf to a JSON string
                req_json = MessageToJson(
                    request, 
                    preserving_proto_field_name=True, 
                    indent=0 # Compact JSON to save space
                )
                span.add_event("ProblemDefinition Received", {
                    "payload.size_bytes": len(req_json),
                    "payload.data": req_json
                })

            try:
                # [ ... Model Building & Solving phases remain the same ... ]
                with tracer.start_as_current_span("Phase.BuildVariables"):
                    modeler = Modeler(request)
                    span.set_attribute("timetabling.model.vars_created", len(modeler.activity_intervals))

                pipeline = [
                    FundamentalConstraintHandler(modeler),
                    StructuralConstraintHandler(modeler),
                    WorkloadConstraintHandler(modeler),
                    PreferenceConstraintHandler(modeler),
                ]
                
                with tracer.start_as_current_span("Phase.ApplyConstraints"):
                    for handler in pipeline:
                        with tracer.start_as_current_span(f"Apply.{handler.__class__.__name__}"):
                            handler.apply(request)

                with tracer.start_as_current_span("Phase.DefineObjective"):
                    modeler.define_objective()

                solver = cp_model.CpSolver()
                if request.config.max_solve_time_seconds > 0:
                    solver.parameters.max_time_in_seconds = request.config.max_solve_time_seconds

                with tracer.start_as_current_span("Phase.CpSatSolve") as solve_span:
                    status = solver.Solve(modeler.model)
                    status_name = solver.StatusName(status)
                    solve_span.set_attribute("solver.status", status_name)
                    solve_span.set_attribute("solver.wall_time_seconds", solver.WallTime())
                    solve_span.set_attribute("solver.branches", solver.NumBranches())
                    solve_span.set_attribute("solver.conflicts", solver.NumConflicts())
                    
                    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                        solve_span.set_attribute("solver.objective_value", solver.ObjectiveValue())
                        
                    span.set_attribute("timetabling.result.status", status_name)

                with tracer.start_as_current_span("Phase.MapSolution"):
                    mapper = SolutionMapper(request, modeler, solver, status)
                    solution = mapper.map_solution()

                # --- 3. VERBOSE OUTPUT LOGGING (Events) ---
                if VERBOSE_TELEMETRY:
                    sol_json = MessageToJson(
                        solution, 
                        preserving_proto_field_name=True,
                        indent=0
                    )
                    span.add_event("Solution Generated", {
                        "payload.size_bytes": len(sol_json),
                        "payload.data": sol_json
                    })

                return solution

            # [ ... Exception handling remains the same ... ]
            except Exception as e:
                span.record_exception(e)
                # ...
