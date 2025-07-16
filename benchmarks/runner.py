import argparse
import json
import multiprocessing
import subprocess
import time
from pathlib import Path

import grpc
import psutil

from src.solver_service.protos import problem_definition_pb2 as problem_pb
from src.solver_service.protos import solution_pb2, solution_pb2_grpc
from .analyzer import analyze_solution
from .generator import generate_problem
from .report import print_report

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
GRPC_PORT = "50051"


def run_solver_process(problem: problem_pb.ProblemDefinition, result_queue: multiprocessing.Queue):
    """
    This function runs in a separate process to call the gRPC solver.
    This isolation is CRITICAL for accurate memory measurement.
    """
    try:
        with grpc.insecure_channel(f'localhost:{GRPC_PORT}') as channel:
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

    server_process = None
    results = []

    try:
        # --- 1. Start the Server Automatically ---
        print("--- Starting Solver Service for benchmark... ---")
        server_process = subprocess.Popen(
            ["poetry", "run", "python", "-m", "src.solver_service.server"]
        )
        # Give the server a moment to start up
        time.sleep(2)

        print("--- Starting Benchmark Suite ---")
        for name, config in PROBLEM_SIZES.items():
            print(f"\nGenerating '{name}' problem...")
            problem = generate_problem(config)

            result_queue = multiprocessing.Queue()
            client_process = multiprocessing.Process(target=run_solver_process, args=(problem, result_queue))

            # --- 2. Measure Performance ---
            start_time = time.perf_counter()
            client_process.start()

            p = psutil.Process(client_process.pid)
            peak_memory_bytes = 0
            while client_process.is_alive():
                try:
                    peak_memory_bytes = max(peak_memory_bytes, p.memory_info().rss)
                except psutil.NoSuchProcess:
                    break
                time.sleep(0.01)

            client_process.join()
            end_time = time.perf_counter()

            # --- 3. Collect Results ---
            result = result_queue.get()
            if isinstance(result, Exception):
                print(f"Error solving '{name}': {result}")
                continue

            run_time = end_time - start_time
            peak_memory_mb = peak_memory_bytes / (1024 * 1024)

            # --- 4. Analyze Solution Quality ---
            quality_metrics = {}
            if result.status in [solution_pb2.OPTIMAL, solution_pb2.FEASIBLE]:
                quality_metrics = analyze_solution(result, problem)

            current_result = {
                "name": name,
                "time": run_time,
                "memory": peak_memory_mb,
                "status": solution_pb2.SolverStatus.Name(result.status),
                "objective": result.quality_score if result.quality_score else "N/A"
            }
            current_result.update(quality_metrics)
            results.append(current_result)

            print(f"'{name}' solved in {run_time:.2f}s, Peak Memory: {peak_memory_mb:.2f} MB")

        # --- 5. Handle Baseline and Reporting ---
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

    finally:
        # --- 6. Guarantee Server Shutdown ---
        if server_process:
            print("\n--- Shutting down Solver Service... ---")
            server_process.terminate()
            server_process.wait()


if __name__ == "__main__":
    main()
