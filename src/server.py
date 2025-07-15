import grpc
from concurrent import futures
import time

import solution_pb2_grpc
from services.timetabling_service import TimetablingService

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    solution_pb2_grpc.add_TimetablingServiceServicer_to_server(
        TimetablingService(), server
    )
    port = "50051"
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Server started, listening on port {port}")
    try:
        while True:
            time.sleep(86400) # One day
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()
