from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProblemDefinition(_message.Message):
    __slots__ = ("job_id", "config", "time_grid", "teachers", "student_groups", "activities")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    TIME_GRID_FIELD_NUMBER: _ClassVar[int]
    TEACHERS_FIELD_NUMBER: _ClassVar[int]
    STUDENT_GROUPS_FIELD_NUMBER: _ClassVar[int]
    ACTIVITIES_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    config: SolverConfig
    time_grid: TimeGrid
    teachers: _containers.RepeatedCompositeFieldContainer[Teacher]
    student_groups: _containers.RepeatedCompositeFieldContainer[StudentGroup]
    activities: _containers.RepeatedCompositeFieldContainer[Activity]
    def __init__(self, job_id: _Optional[str] = ..., config: _Optional[_Union[SolverConfig, _Mapping]] = ..., time_grid: _Optional[_Union[TimeGrid, _Mapping]] = ..., teachers: _Optional[_Iterable[_Union[Teacher, _Mapping]]] = ..., student_groups: _Optional[_Iterable[_Union[StudentGroup, _Mapping]]] = ..., activities: _Optional[_Iterable[_Union[Activity, _Mapping]]] = ...) -> None: ...

class SolverConfig(_message.Message):
    __slots__ = ("max_solve_time_seconds",)
    MAX_SOLVE_TIME_SECONDS_FIELD_NUMBER: _ClassVar[int]
    max_solve_time_seconds: float
    def __init__(self, max_solve_time_seconds: _Optional[float] = ...) -> None: ...

class TimeGrid(_message.Message):
    __slots__ = ("days", "slots_per_day")
    DAYS_FIELD_NUMBER: _ClassVar[int]
    SLOTS_PER_DAY_FIELD_NUMBER: _ClassVar[int]
    days: int
    slots_per_day: int
    def __init__(self, days: _Optional[int] = ..., slots_per_day: _Optional[int] = ...) -> None: ...

class Teacher(_message.Message):
    __slots__ = ("id", "name", "unavailable_slots")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    UNAVAILABLE_SLOTS_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    unavailable_slots: _containers.RepeatedCompositeFieldContainer[TimeSlot]
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., unavailable_slots: _Optional[_Iterable[_Union[TimeSlot, _Mapping]]] = ...) -> None: ...

class StudentGroup(_message.Message):
    __slots__ = ("id", "name")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ...) -> None: ...

class Activity(_message.Message):
    __slots__ = ("id", "name", "teacher_id", "student_group_ids", "duration_in_slots", "is_locked", "locked_start_time")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEACHER_ID_FIELD_NUMBER: _ClassVar[int]
    STUDENT_GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    DURATION_IN_SLOTS_FIELD_NUMBER: _ClassVar[int]
    IS_LOCKED_FIELD_NUMBER: _ClassVar[int]
    LOCKED_START_TIME_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    teacher_id: str
    student_group_ids: _containers.RepeatedScalarFieldContainer[str]
    duration_in_slots: int
    is_locked: bool
    locked_start_time: TimeSlot
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., teacher_id: _Optional[str] = ..., student_group_ids: _Optional[_Iterable[str]] = ..., duration_in_slots: _Optional[int] = ..., is_locked: bool = ..., locked_start_time: _Optional[_Union[TimeSlot, _Mapping]] = ...) -> None: ...

class TimeSlot(_message.Message):
    __slots__ = ("day_index", "slot_index")
    DAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    SLOT_INDEX_FIELD_NUMBER: _ClassVar[int]
    day_index: int
    slot_index: int
    def __init__(self, day_index: _Optional[int] = ..., slot_index: _Optional[int] = ...) -> None: ...
