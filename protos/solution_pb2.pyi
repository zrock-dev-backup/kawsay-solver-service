import problem_definition_pb2 as _problem_definition_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SolverStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNKNOWN: _ClassVar[SolverStatus]
    OPTIMAL: _ClassVar[SolverStatus]
    FEASIBLE: _ClassVar[SolverStatus]
    INFEASIBLE: _ClassVar[SolverStatus]
    MODEL_INVALID: _ClassVar[SolverStatus]
UNKNOWN: SolverStatus
OPTIMAL: SolverStatus
FEASIBLE: SolverStatus
INFEASIBLE: SolverStatus
MODEL_INVALID: SolverStatus

class Solution(_message.Message):
    __slots__ = ("job_id", "status", "scheduled_activities", "message")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    SCHEDULED_ACTIVITIES_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    status: SolverStatus
    scheduled_activities: _containers.RepeatedCompositeFieldContainer[ScheduledActivity]
    message: str
    def __init__(self, job_id: _Optional[str] = ..., status: _Optional[_Union[SolverStatus, str]] = ..., scheduled_activities: _Optional[_Iterable[_Union[ScheduledActivity, _Mapping]]] = ..., message: _Optional[str] = ...) -> None: ...

class ScheduledActivity(_message.Message):
    __slots__ = ("activity_id", "start_time")
    ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    START_TIME_FIELD_NUMBER: _ClassVar[int]
    activity_id: str
    start_time: _problem_definition_pb2.TimeSlot
    def __init__(self, activity_id: _Optional[str] = ..., start_time: _Optional[_Union[_problem_definition_pb2.TimeSlot, _Mapping]] = ...) -> None: ...
