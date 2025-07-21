from typing import List

from ortools.sat.python import cp_model


def create_working_status_variables(
        model: cp_model.CpModel,
        entity_id: str,
        entity_intervals: List[cp_model.IntervalVar],
        day: int,
        slots_per_day: int,
) -> List[cp_model.IntVar]:
    """Creates boolean variables indicating if an entity is active in each slot of a given day."""
    start_of_day = day * slots_per_day
    is_working_per_slot = []

    for slot_idx in range(slots_per_day):
        current_slot_start = start_of_day + slot_idx
        is_working_slot = model.NewBoolVar(f"{entity_id}_day{day}_slot{slot_idx}_working")
        is_working_per_slot.append(is_working_slot)

        # An entity is "working" in a slot if any of its assigned activity intervals cover that slot.
        # Create a literal for each interval that is true if it covers the current slot.
        literals_for_slot = []
        for i, interval in enumerate(entity_intervals):
            lit = model.NewBoolVar(f"{interval.Name()}_covers_{day}_{slot_idx}")

            # Reify: lit is true iff (interval.Start() <= current_slot_start < interval.End())
            start_cond = model.NewBoolVar(f"{lit.Name()}_start_cond")
            model.Add(interval.StartExpr() <= current_slot_start).OnlyEnforceIf(start_cond)
            model.Add(interval.StartExpr() > current_slot_start).OnlyEnforceIf(start_cond.Not())

            end_cond = model.NewBoolVar(f"{lit.Name()}_end_cond")
            model.Add(current_slot_start < interval.EndExpr()).OnlyEnforceIf(end_cond)
            model.Add(current_slot_start >= interval.EndExpr()).OnlyEnforceIf(end_cond.Not())

            model.AddBoolAnd([start_cond, end_cond]).OnlyEnforceIf(lit)
            literals_for_slot.append(lit)

        # is_working_slot is true if ANY of the interval literals for this slot is true.
        if literals_for_slot:
            model.AddBoolOr(literals_for_slot).OnlyEnforceIf(is_working_slot)
            model.Add(is_working_slot == 0).OnlyEnforceIf([l.Not() for l in literals_for_slot])
        else:
            model.Add(is_working_slot == 0)

    return is_working_per_slot


def count_gaps_in_schedule(
        model: cp_model.CpModel,
        entity_id: str,
        day: int,
        is_working: List[cp_model.BoolVarT],
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
) -> List[cp_model.IntVar]:
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
        start_var = interval.StartExpr()

        # Reify the start condition: lit1 is true iff start_var is >= start_of_day
        lit1 = model.NewBoolVar(f"{is_on_day.Name()}_ge")
        model.Add(start_var >= start_of_day).OnlyEnforceIf(lit1)
        model.Add(start_var < start_of_day).OnlyEnforceIf(lit1.Not())

        # Reify the end condition: lit2 is true iff start_var is < end_of_day
        lit2 = model.NewBoolVar(f"{is_on_day.Name()}_lt")
        model.Add(start_var < end_of_day).OnlyEnforceIf(lit2)
        model.Add(start_var >= end_of_day).OnlyEnforceIf(lit2.Not())

        # is_on_day is true iff both conditions are true.
        model.AddBoolAnd([lit1, lit2]).OnlyEnforceIf(is_on_day)
        # If either condition is false, is_on_day must be false.
        model.AddImplication(lit1.Not(), is_on_day.Not())
        model.AddImplication(lit2.Not(), is_on_day.Not())

        literals.append(is_on_day)

    return literals
