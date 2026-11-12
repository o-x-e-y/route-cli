{
  description = "Public transport routes in the Netherlands, door to door, for agents";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      nixpkgs,
      flake-utils,
      ...
    }:
    (flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        packages.default = pkgs.callPackage ./nix/package.nix { };

        devShells.default =
          with pkgs;
          mkShell {
            buildInputs = [
              (python3.withPackages (ps: [ ps.pytest ]))
              ruff
            ];

            shellHook = ''
              export PYTHONPATH="$PWD/src''${PYTHONPATH:+:$PYTHONPATH}"
            '';
          };
      }
    ))
    // {
      overlays.default = final: _prev: {
        route-cli = final.callPackage ./nix/package.nix { };
      };
    };
}
