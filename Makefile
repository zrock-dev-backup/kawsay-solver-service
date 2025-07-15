.PHONY: protoBuild run

protoBuild:
	python -m grpc_tools.protoc \
		-I./protos \
		--python_out=src \
		--pyi_out=src \
		--grpc_python_out=src \
		$(shell find protos -name "*.proto")

run:
	cd src/ && python -m script
