{
  description = "Python Solver Service";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pythonVersion = pkgs.python311;
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonVersion
            poetry
            pkg-config
            protobuf
            zlib
            gcc-unwrapped.lib
            stdenv.cc.cc.lib
          ];

          shellHook = ''
            export LD_LIBRARY_PATH="${pkgs.zlib}/lib:${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"

            # Configure poetry to create venv in project directory
            poetry config virtualenvs.in-project true

            echo "Nix shell activated."
            echo "For first-time setup, run: make setup"
            echo "To enter the environment, run: poetry shell"
            elvish
          '';
        };
      });
}
