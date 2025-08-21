from abc import ABC, abstractmethod

from ..components.modeler import Modeler
from ..protos import problem_definition_pb2 as problem_pb


class BaseConstraintHandler(ABC):
    """
    Abstract base class for all constraint handlers.
    Defines the contract that all concrete handlers must follow.
    """
    def __init__(self, modeler: Modeler):
        self._modeler = modeler
        self._model = modeler.model

    @abstractmethod
    def apply(self, problem: problem_pb.ProblemDefinition) -> None:
        """
        Applies a specific set of constraints to the model.
        This method must be implemented by all concrete subclasses.
        """
        raise NotImplementedError
