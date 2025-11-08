{ pkgs ? import <nixpkgs> {} }:

with pkgs;

let
  pythonEnv = python39.withPackages (ps: with ps; [
    # Add any Python packages here if needed
  ]);
in

mkShell {
  buildInputs = [
    # System dependencies
    gcc
    sqlite
    python39
    # Add any other dependencies here
  ];

  # Environment variables
  shellHook = ''
    export PYTHONPATH="${pythonEnv}/${pythonEnv.sitePackages}:$PYTHONPATH"
  '';
}
