{
  lib,
  python3Packages,
}:

python3Packages.buildPythonApplication {
  pname = "route-cli";
  version = "0.1.0";
  pyproject = true;

  src = lib.cleanSource ../.;

  build-system = [ python3Packages.hatchling ];

  nativeCheckInputs = [ python3Packages.pytestCheckHook ];

  pythonImportsCheck = [ "route" ];

  meta = {
    description = "Public transport routes in the Netherlands, door to door, for agents";
    license = lib.licenses.mit;
    mainProgram = "route";
    platforms = lib.platforms.all;
  };
}
