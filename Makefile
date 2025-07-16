.PHONY: setup install protoBuild run-server run-client benchmark benchmark-update test

# Default goal for new users.
default: setup

# Zero-config onboarding recipe.
setup: install protoBuild
	@echo "\n✅ Project setup complete."
	@echo "--> Run 'poetry shell' to activate the virtual environment."
	@echo "--> Then you can use other make targets like 'make run-server'."

# Installs dependencies via Poetry
install:
	@echo "--- 📦 Installing Python dependencies... ---"
	@poetry install

# Generates Python code from .proto files
protoBuild:
	@echo "--- 🤖 Generating Protobuf files... ---"
	@mkdir -p src/solver_service/protos
	@touch src/solver_service/protos/__init__.py
	@poetry run python -m grpc_tools.protoc \
		-I./protos \
		--python_out=src/solver_service/protos \
		--pyi_out=src/solver_service/protos \
		--grpc_python_out=src/solver_service/protos \
		$(shell find protos -name "*.proto")
	@echo "Protobuf files generated."

# Runs the gRPC server
run-server:
	poetry run python -m solver_service.server

# Runs the test client
run-client:
	poetry run python -m solver_service.client

# Runs the performance benchmarks
benchmark:
	poetry run python -m benchmarks.runner

# Updates the benchmark baseline
benchmark-update:
	poetry run python -m benchmarks.runner --update-baseline

# Runs unit tests
test:
	@echo "Unit tests not implemented."
	# poetry run pytest tests/
