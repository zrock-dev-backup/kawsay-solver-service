.PHONY: protoBuild run-server run-client benchmark benchmark-update test

# Generates Python code from .proto files and places it in src/protos
protoBuild:
	@mkdir -p src/protos
	@touch src/protos/__init__.py
	python -m grpc_tools.protoc \
		-I./protos \
		--python_out=src/protos \
		--pyi_out=src/protos \
		--grpc_python_out=src/protos \
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

# Runs the performance benchmarks against the stored baseline
benchmark:
	@echo "Running performance benchmarks against baseline..."
	python benchmarks/runner.py

# Runs the benchmarks and updates the baseline.json file with the new results
benchmark-update:
	@echo "Running benchmarks and updating baseline.json..."
	python -m benchmarks.runner --update-baseline

# Runs the unit tests (to be implemented)
test:
	@echo "Running unit tests..."
	# pytest tests/
