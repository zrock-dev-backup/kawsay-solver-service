import grpc
from concurrent import futures

from .protos import solution_pb2_grpc
from .services.timetabling_service import TimetablingService
from .telemetry import setup_telemetry

def serve():
    # 1. Initialize OpenTelemetry
    print("Initializing OpenTelemetry...")
    setup_telemetry()

    # 2. Start Server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    solution_pb2_grpc.add_TimetablingServiceServicer_to_server(
        TimetablingService(), server
    )
    port = "50051"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Server started, listening on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Shutdown signal received.")
    finally:
        print("Stopping server...")
        server.stop(0)
        print("Server stopped.")

if __name__ == "__main__":
    serve()
