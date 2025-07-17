from typing import List

from ortools.sat.python import cp_model


def create_working_status_variables(
        model: cp_model.CpModel,
        entity_id: str,
        entity_intervals: List[cp_model.IntervalVar],
        day: int,
        slots_per_day: int,
) -> List[cp_model.BoolVar]:
    """Creates boolean variables indicating if an entity is active in each slot of a given day."""
    start_of_day = day * slots_per_day
    is_working = []

    for slot_idx in range(slots_per_day):
        current_slot_start = start_of_day + slot_idx
        is_working_slot = model.NewBoolVar(f"{entity_id}_day{day}_slot{slot_idx}_working")

        covering_literals = []
        for interval in entity_intervals:
            covers_slot = model.NewBoolVar(f"{interval.Name()}_covers_slot_{day}_{slot_idx}")
            model.Add(interval.StartExpr() <= current_slot_start).OnlyEnforceIf(covers_slot)
            model.Add(interval.EndExpr() > current_slot_start).OnlyEnforceIf(covers_slot)

            model.AddBoolOr(
                [interval.StartExpr() > current_slot_start, interval.EndExpr() <= current_slot_start]
            ).OnlyEnforceIf(covers_slot.Not())

            covering_literals.append(covers_slot)

        if covering_literals:
            model.AddBoolOr(covering_literals).OnlyEnforceIf(is_working_slot)
            model.Add(is_working_slot == 0).OnlyEnforceIf([lit.Not() for lit in covering_literals])
        else:
            model.Add(is_working_slot == 0)

        is_working.append(is_working_slot)

    return is_working


def count_gaps_in_schedule(
        model: cp_model.CpModel,
        entity_id: str,
        day: int,
        is_working: List[cp_model.BoolVar],
) -> cp_model.IntVar:
    """Counts gaps: non-working slots between the first and last working slots of the day."""
    slots_per_day = len(is_working)

    first_work_slot = model.NewIntVar(-1, slots_per_day - 1, f"{entity_id}_day{day}_first_work")
    last_work_slot = model.NewIntVar(-1, slots_per_day - 1, f"{entity_id}_day{day}_last_work")

    # Find first and last working slot indices
    for i in range(slots_per_day):
        model.Add(first_work_slot == i).OnlyEnforceIf(is_working[i]).OnlyEnforceIf(
            [is_working[j].Not() for j in range(i)]
        )
        model.Add(last_work_slot == i).OnlyEnforceIf(is_working[i]).OnlyEnforceIf(
            [is_working[j].Not() for j in range(i + 1, slots_per_day)]
        )

    # Handle case with no work
    no_work_on_day = model.NewBoolVar(f"{entity_id}_day{day}_no_work")
    model.Add(sum(is_working) == 0).OnlyEnforceIf(no_work_on_day)
    model.Add(first_work_slot == -1).OnlyEnforceIf(no_work_on_day)
    model.Add(last_work_slot == -1).OnlyEnforceIf(no_work_on_day)

    total_work_duration = model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_work_duration")
    model.Add(total_work_duration == sum(is_working))

    span_duration = model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_span")
    model.Add(span_duration == last_work_slot - first_work_slot + 1)

    gaps = model.NewIntVar(0, slots_per_day, f"{entity_id}_day{day}_gaps")
    model.Add(gaps == span_duration - total_work_duration)
    model.Add(gaps == 0).OnlyEnforceIf(no_work_on_day)

    return gaps


def get_day_active_literals(
    model: cp_model.CpModel,
    intervals: List[cp_model.IntervalVar],
    day: int,
    slots_per_day: int,
    prefix: str
) -> List[cp_model.BoolVar]:
    """
    Creates boolean variables indicating if an interval starts on a given day.
    This establishes a full "iff" relationship for robustness.

    Args:
        model: The CpModel instance.
        intervals: A list of IntervalVar for which to create literals.
        day: The day index to check against.
        slots_per_day: The number of slots in a day.
        prefix: A unique prefix for the new variable names.

    Returns:
        A list of boolean variables, one for each interval. Each variable is true
        if its corresponding interval starts on the specified day.
    """
    start_of_day = day * slots_per_day
    end_of_day = start_of_day + slots_per_day
    literals = []

    for i, interval in enumerate(intervals):
        is_on_day = model.NewBoolVar(f"{prefix}_on_day_{day}_interval_{i}")

        # Forward: is_on_day => interval is within day bounds
        model.Add(interval.StartExpr() >= start_of_day).OnlyEnforceIf(is_on_day)
        model.Add(interval.StartExpr() < end_of_day).OnlyEnforceIf(is_on_day)

        # Reverse: interval is outside day bounds => NOT is_on_day
        lit_before = model.NewBoolVar(f"{prefix}_before_day_{day}_interval_{i}")
        model.Add(interval.StartExpr() < start_of_day).OnlyEnforceIf(lit_before)
        model.AddImplication(lit_before, is_on_day.Not())

        lit_after = model.NewBoolVar(f"{prefix}_after_day_{day}_interval_{i}")
        model.Add(interval.StartExpr() >= end_of_day).OnlyEnforceIf(lit_after)
        model.AddImplication(lit_after, is_on_day.Not())

        literals.append(is_on_day)

    return literals
