import pytest
from ortools.sat.python import cp_model

from src.solver_service.components.modeler import Modeler
from src.solver_service.protos import problem_definition_pb2 as problem_pb


class SolveResult:
    """A simple container for solver results."""
    def __init__(self, status: int, objective_value: float):
        self.status = status
        self.objective_value = objective_value
        self.status_name = cp_model.CpSolver().StatusName(status)

    def __repr__(self):
        return f"<SolveResult status={self.status_name} objective={self.objective_value}>"


@pytest.fixture
def solve_model():
    """Factory fixture to solve a model and return a structured result."""
    def _solver(modeler: Modeler) -> SolveResult:
        solver = cp_model.CpSolver()
        status = solver.Solve(modeler.model)
        return SolveResult(status, solver.ObjectiveValue())
    return _solver


def create_problem(days: int, slots_per_day: int) -> problem_pb.ProblemDefinition:
    """Helper to create a basic problem definition."""
    problem = problem_pb.ProblemDefinition()
    problem.time_grid.days = days
    problem.time_grid.slots_per_day = slots_per_day
    return problem
