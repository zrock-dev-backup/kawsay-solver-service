{
  description = "Python";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            python311
            poetry

            pkg-config
            protobuf
            zlib

            gcc-unwrapped.lib
            stdenv.cc.cc.lib
          ];

          shellHook = ''
          export LD_LIBRARY_PATH="${pkgs.zlib}/lib:${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
            # Initialize poetry project if pyproject.toml doesn't exist
            if [ ! -f "pyproject.toml" ]; then
              echo "Initializing Poetry project..."
              poetry init --no-interaction --name "arduino-python-project" --version "0.1.0"
              # Add your dependencies
              poetry add grpcio grpcio-tools google-api-python-client ortools
            fi

            # Configure poetry to create venv in project directory
            poetry config virtualenvs.in-project true
            poetry config virtualenvs.prefer-active-python true

            # Install dependencies and activate virtual environment
            echo "Installing dependencies with Poetry..."
            poetry install

            # Activate the poetry environment
            source $(poetry env info --path)/bin/activate

            echo "Poetry environment activated!"
            echo "Python virtual environment: $(which python)"
            echo "To add packages: poetry add <package>"
            echo "To remove packages: poetry remove <package>"
            echo "To update packages: poetry update"
            elvish
          '';
        };
      }
    );
}
