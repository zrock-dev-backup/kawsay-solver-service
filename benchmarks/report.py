import sys


# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_report(results: list, baseline: dict, regression_threshold: float = 0.15):
    """
    Prints a formatted report comparing benchmark results to a baseline.

    Args:
        results: A list of dictionaries, each containing the results of a run.
        baseline: A dictionary containing the baseline results.
        regression_threshold: The percentage (e.g., 0.15 for 15%) of performance
                              decrease that is considered a failure.
    """
    header = f"{'Problem Size':<15} | {'Status':<10} | {'Time (s)':<10} | {'Objective':<12} | {'Memory (MB)':<14} | {'Baseline Comparison':<25}"
    print(f"{Colors.BOLD}{Colors.HEADER}{header}{Colors.ENDC}")
    print("-" * len(header))

    overall_pass = True

    for res in results:
        name = res['name']
        base = baseline.get(name, {})

        # Format current results
        time_str = f"{res['time']:.2f}"
        mem_str = f"{res['memory']:.2f}"
        obj_str = f"{res.get('objective', 'N/A')}"

        # Compare to baseline
        comparison_str = ""
        is_failure = False
        if base:
            time_base = base.get('time', 0)
            if time_base > 0:
                diff = (res['time'] - time_base) / time_base
                sign = "+" if diff >= 0 else ""
                color = Colors.FAIL if diff > regression_threshold else Colors.OKGREEN
                if diff > regression_threshold:
                    is_failure = True
                comparison_str = f"{color}{sign}{diff:.1%}{Colors.ENDC}"
        else:
            comparison_str = f"{Colors.OKBLUE}New baseline{Colors.ENDC}"

        row_color = Colors.FAIL if is_failure else ""
        if res['name'] == "Medium" and is_failure:
            overall_pass = False

        print(
            f"{row_color}{name:<15}{Colors.ENDC} | {res['status']:<10} | {time_str:<10} | {obj_str:<12} | {mem_str:<14} | {comparison_str:<25}")

    if not overall_pass:
        print(
            f"\n{Colors.FAIL}{Colors.BOLD}CI CHECK FAILED:{Colors.ENDC}{Colors.FAIL} 'Medium' problem regressed by more than {regression_threshold:.0%}.{Colors.ENDC}")
        sys.exit(1)
    else:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}CI CHECK PASSED.{Colors.ENDC}")
