# Makefile

.PHONY: protoBuild run-server run-client

# Generates Python code from .proto files and places it in src/protos
protoBuild:
	@mkdir -p src/protos
	@touch src/protos/__init__.py
	python -m grpc_tools.protoc \
		-I./protos \
		--python_out=src \
		--pyi_out=src \
		--grpc_python_out=src \
		$(shell find protos -name "*.proto")
	@echo "Protobuf files generated successfully in src/protos/"

# Runs the gRPC server
run-server:
	@echo "Starting gRPC server..."
	python src/server.py

# Runs the test client to call the server
run-client:
	@echo "Running test client..."
	python src/client.py
