{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.route;

  env = {
    ROUTE_MAX_REQUESTS = toString cfg.limit.requests;
    ROUTE_LIMIT_DAYS = toString cfg.limit.days;
  }
  // lib.optionalAttrs (cfg.keyFile != null) { ROUTE_GOOGLE_KEY_FILE = cfg.keyFile; };

  # Wrapped rather than exported as session variables, so the settings reach the
  # binary whatever starts it: a login shell, Claude Code, a systemd unit.
  wrapped = pkgs.symlinkJoin {
    name = "${cfg.package.name}-wrapped";
    paths = [ cfg.package ];
    nativeBuildInputs = [ pkgs.makeWrapper ];
    postBuild = ''
      wrapProgram $out/bin/route ${
        lib.concatStrings (lib.mapAttrsToList (k: v: " --set-default ${k} ${lib.escapeShellArg v}") env)
      }
    '';
  };
in
{
  options.programs.route = {
    enable = lib.mkEnableOption "the route CLI";

    package = lib.mkOption {
      type = lib.types.package;
      default = pkgs.callPackage ./package.nix { };
      defaultText = lib.literalMD "this flake's package, built with your `pkgs`";
      description = "The package to install.";
    };

    keyFile = lib.mkOption {
      type = lib.types.nullOr lib.types.str;
      default = null;
      example = "/run/secrets/routes-api-key";
      description = ''
        File holding the Google Maps Platform key (Routes API), passed as
        $ROUTE_GOOGLE_KEY_FILE. A path string, so the key never enters the store.
      '';
    };

    limit = {
      requests = lib.mkOption {
        type = lib.types.ints.unsigned;
        default = 600;
        description = "At most this many Google requests per `limit.days` days.";
      };

      days = lib.mkOption {
        type = lib.types.ints.positive;
        default = 7;
        description = "The window `limit.requests` counts over, in days.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    home.packages = [ wrapped ];
  };
}
