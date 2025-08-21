# src/solver_service/handlers/structural_handler.py

from ortools.sat.python import cp_model

from ..protos import problem_definition_pb2 as problem_pb
from .base_handler import BaseConstraintHandler


class StructuralConstraintHandler(BaseConstraintHandler):
    """
    Applies hard constraints that define relationships between activities.
    - Activity A must happen before Activity B.
    - Activity A must be immediately followed by Activity B.
    - A minimum number of days must pass between Activity A and B.
    """
    def apply(self, problem: problem_pb.ProblemDefinition) -> None:
        self._enforce_activity_ordering(problem)
        self._enforce_consecutive_activities(problem)
        self._enforce_min_days_between(problem)

    def _enforce_activity_ordering(self, problem: problem_pb.ProblemDefinition) -> None:
        """Activity A must end before or when Activity B begins."""
        for ordering in problem.activity_orderings:
            before_interval = self._modeler.activity_intervals[ordering.before_activity_id]
            after_interval = self._modeler.activity_intervals[ordering.after_activity_id]
            self._model.Add(before_interval.EndExpr() <= after_interval.StartExpr())

    def _enforce_consecutive_activities(self, problem: problem_pb.ProblemDefinition) -> None:
        """Activity A must be immediately followed by Activity B ON THE SAME DAY."""
        for consecutive in problem.consecutive_activities:
            # --- CORRECCIÓN: Definir los IDs antes de usarlos ---
            first_id = consecutive.first_activity_id
            second_id = consecutive.second_activity_id

            # Obtener los intervalos del modelo
            first_interval = self._modeler.activity_intervals[first_id]
            second_interval = self._modeler.activity_intervals[second_id]

            # Forzar a que ambas actividades estén en el mismo día.
            first_day = self._get_day_of_activity(first_id)
            second_day = self._get_day_of_activity(second_id)
            self._model.Add(first_day == second_day)

            # Mantener la restricción original para que sean consecutivas en el tiempo.
            self._model.Add(first_interval.EndExpr() == second_interval.StartExpr())

    def _enforce_min_days_between(self, problem: problem_pb.ProblemDefinition) -> None:
        """A minimum number of full days must pass between two activities."""
        slots_per_day = problem.time_grid.slots_per_day
        if slots_per_day <= 0:
            return

        for min_days in problem.min_days_between_activities:
            act1_day = self._get_day_of_activity(min_days.first_activity_id)
            act2_day = self._get_day_of_activity(min_days.second_activity_id)

            day_diff = self._model.NewIntVar(
                0, problem.time_grid.days, f"day_diff_{min_days.first_activity_id}_{min_days.second_activity_id}"
            )
            self._model.AddAbsEquality(day_diff, act1_day - act2_day)
            self._model.Add(day_diff >= min_days.minimum_days)

    def _get_day_of_activity(self, activity_id: str) -> cp_model.IntVar:
        """Helper to get a variable representing the day index of an activity."""
        slots_per_day = self._modeler.problem.time_grid.slots_per_day
        start_var = self._modeler.activity_intervals[activity_id].StartExpr()
        day_var = self._model.NewIntVar(0, self._modeler.problem.time_grid.days - 1, f"day_{activity_id}")
        self._model.AddDivisionEquality(day_var, start_var, slots_per_day)
        return day_var
