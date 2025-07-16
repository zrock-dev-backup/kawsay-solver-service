.PHONY: setup install protoBuild run-server run-client benchmark benchmark-update test

# Default goal for new users.
default: setup

# Zero-config onboarding recipe. Installs the project in editable mode.
setup: install protoBuild
	@echo "\n✅ Project setup complete."
	@echo "--> Run 'poetry shell' to activate the virtual environment."
	@echo "--> Then you can use other make targets like 'make run-server' or 'make benchmark'."

# Installs dependencies via Poetry and the project itself in editable mode.
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
		--python_out=src/solver_service \
		--pyi_out=src/solver_service \
		--grpc_python_out=src/solver_service \
		$(shell find protos -name "*.proto")
	@echo "Protobuf files generated."

# Runs the gRPC server
run-server:
	poetry run python -m solver_service.server

# Runs the test client
run-client:
	poetry run python -m solver_service.client

# Runs the performance benchmarks against the baseline
benchmark:
	@echo "--- 📊 Running performance benchmarks... ---"
	poetry run python -m benchmarks.runner

# Runs benchmarks and updates the baseline.json file
benchmark-update:
	@echo "--- 📝 Running benchmarks and updating baseline... ---"
	poetry run python -m benchmarks.runner --update-baseline

# Runs unit tests
test:
	@echo "--- 🧪 Running unit tests... ---"
	poetry run pytest tests/
