import argparse
import json
import multiprocessing
import sys
import time
from pathlib import Path

import grpc
import psutil

# Project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.protos import problem_definition_pb2 as problem_pb
from src.protos import solution_pb2_grpc
from benchmarks.generator import generate_problem
from benchmarks.report import print_report

# Define the configurations for each problem size
PROBLEM_SIZES = {
    "Small": {"name": "Small", "num_teachers": 10, "num_groups": 5, "num_activities": 50, "lock_percent": 0.05,
              "unavail_percent": 0.1},
    "Medium": {"name": "Medium", "num_teachers": 40, "num_groups": 20, "num_activities": 200, "lock_percent": 0.05,
               "unavail_percent": 0.2},
    "Large": {"name": "Large", "num_teachers": 100, "num_groups": 50, "num_activities": 500, "lock_percent": 0.05,
              "unavail_percent": 0.2},
}

BASELINE_FILE = Path(__file__).parent / "baseline.json"


def run_solver_process(problem: problem_pb.ProblemDefinition, result_queue: multiprocessing.Queue):
    """
    This function runs in a separate process to call the gRPC solver.
    This isolation is CRITICAL for accurate memory measurement.
    """
    try:
        with grpc.insecure_channel('localhost:50051') as channel:
            stub = solution_pb2_grpc.TimetablingServiceStub(channel)
            solution = stub.Solve(problem)
            result_queue.put(solution)
    except Exception as e:
        result_queue.put(e)


def main():
    parser = argparse.ArgumentParser(description="Run performance benchmarks for the solver service.")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Update the baseline.json file with the current results.")
    args = parser.parse_args()

    results = []

    print("--- Starting Benchmark Suite ---")
    for name, config in PROBLEM_SIZES.items():
        print(f"\nGenerating '{name}' problem...")
        problem = generate_problem(config)

        result_queue = multiprocessing.Queue()
        solver_process = multiprocessing.Process(target=run_solver_process, args=(problem, result_queue))

        # --- Measure Performance ---
        start_time = time.perf_counter()
        solver_process.start()

        p = psutil.Process(solver_process.pid)
        peak_memory_bytes = 0
        while solver_process.is_alive():
            try:
                peak_memory_bytes = max(peak_memory_bytes, p.memory_info().rss)
            except psutil.NoSuchProcess:
                break
            time.sleep(0.01)

        solver_process.join()
        end_time = time.perf_counter()

        # --- Collect Results ---
        result = result_queue.get()
        if isinstance(result, Exception):
            print(f"Error solving '{name}': {result}")
            continue

        run_time = end_time - start_time
        peak_memory_mb = peak_memory_bytes / (1024 * 1024)

        results.append({
            "name": name,
            "time": run_time,
            "memory": peak_memory_mb,
            "status": result.SolverStatus.Name(result.status),
            "objective": result.quality_score if result.quality_score else "N/A"
        })
        print(f"'{name}' solved in {run_time:.2f}s, Peak Memory: {peak_memory_mb:.2f} MB")

    # --- Handle Baseline and Reporting ---
    try:
        with open(BASELINE_FILE, 'r') as f:
            baseline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        baseline = {}

    print("\n--- Benchmark Report ---")
    print_report(results, baseline)

    if args.update_baseline:
        new_baseline = {res['name']: {"time": res['time'], "objective": res['objective']} for res in results}
        with open(BASELINE_FILE, 'w') as f:
            json.dump(new_baseline, f, indent=2)
        print(f"\nBaseline updated in {BASELINE_FILE}")


if __name__ == "__main__":
    main()
