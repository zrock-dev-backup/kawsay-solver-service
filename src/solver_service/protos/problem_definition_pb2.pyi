from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ProblemDefinition(_message.Message):
    __slots__ = ("job_id", "config", "time_grid", "teachers", "student_groups", "activities", "workload_constraints", "advanced_workload_constraints", "system_breaks", "time_preferences", "student_gap_penalty_per_day", "activity_orderings", "consecutive_activities", "min_days_between_activities")
    JOB_ID_FIELD_NUMBER: _ClassVar[int]
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    TIME_GRID_FIELD_NUMBER: _ClassVar[int]
    TEACHERS_FIELD_NUMBER: _ClassVar[int]
    STUDENT_GROUPS_FIELD_NUMBER: _ClassVar[int]
    ACTIVITIES_FIELD_NUMBER: _ClassVar[int]
    WORKLOAD_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    ADVANCED_WORKLOAD_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    SYSTEM_BREAKS_FIELD_NUMBER: _ClassVar[int]
    TIME_PREFERENCES_FIELD_NUMBER: _ClassVar[int]
    STUDENT_GAP_PENALTY_PER_DAY_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_ORDERINGS_FIELD_NUMBER: _ClassVar[int]
    CONSECUTIVE_ACTIVITIES_FIELD_NUMBER: _ClassVar[int]
    MIN_DAYS_BETWEEN_ACTIVITIES_FIELD_NUMBER: _ClassVar[int]
    job_id: str
    config: SolverConfig
    time_grid: TimeGrid
    teachers: _containers.RepeatedCompositeFieldContainer[Teacher]
    student_groups: _containers.RepeatedCompositeFieldContainer[StudentGroup]
    activities: _containers.RepeatedCompositeFieldContainer[Activity]
    workload_constraints: _containers.RepeatedCompositeFieldContainer[WorkloadConstraint]
    advanced_workload_constraints: _containers.RepeatedCompositeFieldContainer[AdvancedWorkloadConstraint]
    system_breaks: _containers.RepeatedCompositeFieldContainer[SystemBreak]
    time_preferences: _containers.RepeatedCompositeFieldContainer[TimePreference]
    student_gap_penalty_per_day: int
    activity_orderings: _containers.RepeatedCompositeFieldContainer[ActivityOrdering]
    consecutive_activities: _containers.RepeatedCompositeFieldContainer[ConsecutiveActivities]
    min_days_between_activities: _containers.RepeatedCompositeFieldContainer[MinDaysBetweenActivities]
    def __init__(self, job_id: _Optional[str] = ..., config: _Optional[_Union[SolverConfig, _Mapping]] = ..., time_grid: _Optional[_Union[TimeGrid, _Mapping]] = ..., teachers: _Optional[_Iterable[_Union[Teacher, _Mapping]]] = ..., student_groups: _Optional[_Iterable[_Union[StudentGroup, _Mapping]]] = ..., activities: _Optional[_Iterable[_Union[Activity, _Mapping]]] = ..., workload_constraints: _Optional[_Iterable[_Union[WorkloadConstraint, _Mapping]]] = ..., advanced_workload_constraints: _Optional[_Iterable[_Union[AdvancedWorkloadConstraint, _Mapping]]] = ..., system_breaks: _Optional[_Iterable[_Union[SystemBreak, _Mapping]]] = ..., time_preferences: _Optional[_Iterable[_Union[TimePreference, _Mapping]]] = ..., student_gap_penalty_per_day: _Optional[int] = ..., activity_orderings: _Optional[_Iterable[_Union[ActivityOrdering, _Mapping]]] = ..., consecutive_activities: _Optional[_Iterable[_Union[ConsecutiveActivities, _Mapping]]] = ..., min_days_between_activities: _Optional[_Iterable[_Union[MinDaysBetweenActivities, _Mapping]]] = ...) -> None: ...

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
    __slots__ = ("id", "name", "teacher_id", "student_group_ids", "duration_in_slots", "is_locked", "locked_start_time", "time_preference_id")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEACHER_ID_FIELD_NUMBER: _ClassVar[int]
    STUDENT_GROUP_IDS_FIELD_NUMBER: _ClassVar[int]
    DURATION_IN_SLOTS_FIELD_NUMBER: _ClassVar[int]
    IS_LOCKED_FIELD_NUMBER: _ClassVar[int]
    LOCKED_START_TIME_FIELD_NUMBER: _ClassVar[int]
    TIME_PREFERENCE_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    teacher_id: str
    student_group_ids: _containers.RepeatedScalarFieldContainer[str]
    duration_in_slots: int
    is_locked: bool
    locked_start_time: TimeSlot
    time_preference_id: str
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., teacher_id: _Optional[str] = ..., student_group_ids: _Optional[_Iterable[str]] = ..., duration_in_slots: _Optional[int] = ..., is_locked: bool = ..., locked_start_time: _Optional[_Union[TimeSlot, _Mapping]] = ..., time_preference_id: _Optional[str] = ...) -> None: ...

class TimeSlot(_message.Message):
    __slots__ = ("day_index", "slot_index")
    DAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    SLOT_INDEX_FIELD_NUMBER: _ClassVar[int]
    day_index: int
    slot_index: int
    def __init__(self, day_index: _Optional[int] = ..., slot_index: _Optional[int] = ...) -> None: ...

class WorkloadConstraint(_message.Message):
    __slots__ = ("teacher_id", "max_gaps_per_day", "penalty_per_gap", "max_hours_per_day")
    TEACHER_ID_FIELD_NUMBER: _ClassVar[int]
    MAX_GAPS_PER_DAY_FIELD_NUMBER: _ClassVar[int]
    PENALTY_PER_GAP_FIELD_NUMBER: _ClassVar[int]
    MAX_HOURS_PER_DAY_FIELD_NUMBER: _ClassVar[int]
    teacher_id: str
    max_gaps_per_day: int
    penalty_per_gap: int
    max_hours_per_day: int
    def __init__(self, teacher_id: _Optional[str] = ..., max_gaps_per_day: _Optional[int] = ..., penalty_per_gap: _Optional[int] = ..., max_hours_per_day: _Optional[int] = ...) -> None: ...

class AdvancedWorkloadConstraint(_message.Message):
    __slots__ = ("teacher_id", "max_hours_per_week", "max_days_per_week")
    TEACHER_ID_FIELD_NUMBER: _ClassVar[int]
    MAX_HOURS_PER_WEEK_FIELD_NUMBER: _ClassVar[int]
    MAX_DAYS_PER_WEEK_FIELD_NUMBER: _ClassVar[int]
    teacher_id: str
    max_hours_per_week: int
    max_days_per_week: int
    def __init__(self, teacher_id: _Optional[str] = ..., max_hours_per_week: _Optional[int] = ..., max_days_per_week: _Optional[int] = ...) -> None: ...

class SystemBreak(_message.Message):
    __slots__ = ("id", "start_day", "end_day")
    ID_FIELD_NUMBER: _ClassVar[int]
    START_DAY_FIELD_NUMBER: _ClassVar[int]
    END_DAY_FIELD_NUMBER: _ClassVar[int]
    id: str
    start_day: int
    end_day: int
    def __init__(self, id: _Optional[str] = ..., start_day: _Optional[int] = ..., end_day: _Optional[int] = ...) -> None: ...

class TimePreference(_message.Message):
    __slots__ = ("id", "preferred_slots", "penalty_per_violation")
    ID_FIELD_NUMBER: _ClassVar[int]
    PREFERRED_SLOTS_FIELD_NUMBER: _ClassVar[int]
    PENALTY_PER_VIOLATION_FIELD_NUMBER: _ClassVar[int]
    id: str
    preferred_slots: _containers.RepeatedScalarFieldContainer[int]
    penalty_per_violation: int
    def __init__(self, id: _Optional[str] = ..., preferred_slots: _Optional[_Iterable[int]] = ..., penalty_per_violation: _Optional[int] = ...) -> None: ...

class ActivityOrdering(_message.Message):
    __slots__ = ("before_activity_id", "after_activity_id")
    BEFORE_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    AFTER_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    before_activity_id: str
    after_activity_id: str
    def __init__(self, before_activity_id: _Optional[str] = ..., after_activity_id: _Optional[str] = ...) -> None: ...

class ConsecutiveActivities(_message.Message):
    __slots__ = ("first_activity_id", "second_activity_id")
    FIRST_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    SECOND_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    first_activity_id: str
    second_activity_id: str
    def __init__(self, first_activity_id: _Optional[str] = ..., second_activity_id: _Optional[str] = ...) -> None: ...

class MinDaysBetweenActivities(_message.Message):
    __slots__ = ("first_activity_id", "second_activity_id", "minimum_days")
    FIRST_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    SECOND_ACTIVITY_ID_FIELD_NUMBER: _ClassVar[int]
    MINIMUM_DAYS_FIELD_NUMBER: _ClassVar[int]
    first_activity_id: str
    second_activity_id: str
    minimum_days: int
    def __init__(self, first_activity_id: _Optional[str] = ..., second_activity_id: _Optional[str] = ..., minimum_days: _Optional[int] = ...) -> None: ...
