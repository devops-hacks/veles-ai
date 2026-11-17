# nix/inference.nix - GGUF inference core (roadmap PR 3)
# llama-swap as a system LaunchDaemon behind loopback-only binds, A1 keys
# sops-managed, plus the isolated autocomplete tier (own llama-server,
# outside the swap matrix). sync-models (download/verify/timer) is PR 4.
#
# Trust anchor for the llama-swap binary (bootstrap.sh precedent):
# - pinned by VERSION (LLAMA_SWAP_VERSION) AND content hash
#   (LLAMA_SWAP_SHA256, SRI form) - both named constants here, one place.
# - hash taken from the GitHub release asset digest via API at authoring
#   time; upstream ships no checksums file for release assets, so this
#   in-repo hash IS the verification.
# - changing either constant is a reviewed PR, never an in-place edit.
#
# Identity is operator-handled (tier-0 pattern): sops.age.keyFile points
# at an operator-created path; this module never creates, moves, or
# decrypts keys. No username of any person appears here - the service
# account is project-named (the PII ruling, ADR-0004 context).

{
  config,
  pkgs,
  lib,
  ...
}:

let
  # ---- pinned constants (change only via reviewed PR) ----
  LLAMA_SWAP_VERSION = "268";
  LLAMA_SWAP_SHA256 = "sha256-NzobtQFBgORKkaXnp6ok8boYtd/ZYid596ojS9M+7IY=";

  MODELS_ROOT = "/Volumes/ai-models/gguf";
  AUTOCOMPLETE_DEST = "qwen2.5-coder-1.5b-q8_0.gguf"; # manifest dest, 1.5B tier

  # llama-swap release asset (darwin arm64), pinned twice (version + hash)
  llama-swap = pkgs.stdenv.mkDerivation {
    pname = "llama-swap";
    version = LLAMA_SWAP_VERSION;
    src = pkgs.fetchurl {
      url = "https://github.com/mostlygeek/llama-swap/releases/download/v${LLAMA_SWAP_VERSION}/llama-swap_${LLAMA_SWAP_VERSION}_darwin_arm64.tar.gz";
      sha256 = LLAMA_SWAP_SHA256;
    };
    sourceRoot = ".";
    # source tarball carries the prebuilt darwin-arm64 binary at top level
    installPhase = ''
      install -Dm755 llama-swap $out/bin/llama-swap
    '';
  };

  # generated router config + isolated-tier cmd lines (see the generator)
  swapConfig = pkgs.runCommand "llama-swap-config"
    {
      nativeBuildInputs = [ pkgs.python3 ];
    }
    ''
      python3 ${../scripts/generate_swap_config.py} \
        --manifest ${../models/models.toml} \
        --llama-server ${pkgs.llama-cpp}/bin/llama-server \
        --models-root ${MODELS_ROOT} \
        --out-dir $out
    '';

  # ---- launchers: secrets enter the environment here, nowhere else ----
  # sops-nix materializes secret files under /run/secrets on darwin;
  # paths are referenced symbolically via config.sops.secrets.<name>.path.
  llamaSwapLauncher = pkgs.writeShellScript "llama-swap-launcher" ''
    export LLAMA_SWAP_KEY_OPERATOR="$(cat ${config.sops.secrets."llama_swap/key_operator".path})"
    export LLAMA_SWAP_KEY_FAMILY="$(cat ${config.sops.secrets."llama_swap/key_family".path})"
    export LLAMA_SWAP_KEY_AGENTS="$(cat ${config.sops.secrets."llama_swap/key_agents".path})"
    exec ${llama-swap}/bin/llama-swap -config ${swapConfig}/config.yml -listen 127.0.0.1:4002
  '';

  llamaAutocompleteLauncher = pkgs.writeShellScript "llama-autocomplete-launcher" ''
    MODEL="${MODELS_ROOT}/${AUTOCOMPLETE_DEST}"
    if [ ! -f "$MODEL" ]; then
      echo "llama-autocomplete: model absent (sync-models lands in roadmap PR 4) - staying down, no crash loop"
      exit 0
    fi
    KEY="$(cat ${config.sops.secrets."llama_swap/key_operator".path})"
    # shellcheck disable=SC2046 - the cmd file is a command line by contract
    exec $(cat ${swapConfig}/isolated-qwen2.5-coder-1.5b.cmd) --api-key "$KEY"
  '';
  # sync-models timer launcher: python comes from nix (no CLT dependency
  # in the system-daemon context); manifest + root are store-pinned.
  syncModelsLauncher = pkgs.writeShellScript "sync-models-launcher" ''
    export SYNC_PYTHON="${pkgs.python3}/bin/python3"
    export MODELS_ROOT="${MODELS_ROOT}"
    export MANIFEST="${../models/models.toml}"
    exec ${../scripts/sync-models.sh}
  '';
in
{
  # ---- hidden service account: project-named, never a person (PII ruling) ----
  # Pattern (b), architect-approved: this module declares NO user
  # accounts - the operator creates the hidden service account once
  # (runbook: dscl tier-0 step). Root-cause note (probe + bisect in
  # docs/inference.md): the launchd recursion was derivation-as-Program,
  # NOT UserName - fixed via command = "<wrapper path>" below; the
  # users-declaration removal stands per the ruling (smaller surface,
  # same config).

  # ---- sops: age identity + the three A1 gateway keys ----
  # Operator-created symlink keeps the per-user key reachable for the
  # system daemon context; creating/backing it up stays with the operator.
  sops.age.keyFile = "/Users/Shared/veles/sops/age/keys.txt";

  sops.secrets."llama_swap/key_operator" = {
    sopsFile = ../secrets/llama-swap.yaml;
    owner = "_veles";
    mode = "0400";
  };
  sops.secrets."llama_swap/key_family" = {
    sopsFile = ../secrets/llama-swap.yaml;
    owner = "_veles";
    mode = "0400";
  };
  sops.secrets."llama_swap/key_agents" = {
    sopsFile = ../secrets/llama-swap.yaml;
    owner = "_veles";
    mode = "0400";
  };

  launchd.daemons.llama-swap = {
    command = "${llamaSwapLauncher}";
    serviceConfig = {
      UserName = "_veles";
      KeepAlive.SuccessfulExit = false;
      RunAtLoad = true;
    };
  };

  launchd.daemons.llama-autocomplete = {
    command = "${llamaAutocompleteLauncher}";
    serviceConfig = {
      UserName = "_veles";
      KeepAlive.SuccessfulExit = false;
      RunAtLoad = true;
    };
  };

  # ---- sync-models: batch download/verify timer (roadmap PR 4) ----
  # Batch job: no RunAtLoad, no KeepAlive (failure = loud .err, no loop).
  # Its logs land in /var/log/veles (activation pre-creates + pre-owns
  # them); ROUTER stdout redirection stays a Phase 2 item
  # (docs/inference.md, "Logs and Metal verification").
  launchd.daemons.sync-models = {
    command = "${syncModelsLauncher}";
    serviceConfig = {
      UserName = "_veles";
      RunAtLoad = false;
      StartCalendarInterval = { Hour = 4; Minute = 30; };
      StandardOutPath = "/var/log/veles/sync-models.out";
      StandardErrorPath = "/var/log/veles/sync-models.err";
    };
  };

  # ---- activation: model volume ownership (operator prepares the volume) ----
  system.activationScripts.llamaModelsVolume = {
    enable = true;
    text = ''
      if [ -d "${MODELS_ROOT}" ]; then
        if /usr/sbin/chown -R _veles:_veles "${MODELS_ROOT}"; then
          echo "veles: model volume ownership verified (_veles:_veles)"
        else
          echo "veles: MARKER-A2 CHOWN FAILED for ${MODELS_ROOT}"
          echo "veles: root cause + runbook: docs/inference.md finding 9"
          echo "veles: services stay up; sync-models stays down until fixed"
        fi
      else
        echo "veles: ${MODELS_ROOT} absent - prepare the volume (operator step); services stay up without models"
      fi
    '';
  };

  # sync-models log home: launchd truncates/creates the files itself but
  # not the directory; pre-create + pre-own so the _veles job can write
  # its evidence there.
  system.activationScripts.velesLogDir = {
    enable = true;
    text = ''
      /bin/mkdir -p /var/log/veles
      /bin/chmod 0755 /var/log/veles
      /usr/sbin/chown root:admin /var/log/veles
      /usr/bin/touch /var/log/veles/sync-models.out /var/log/veles/sync-models.err
      /usr/sbin/chown _veles:_veles /var/log/veles/sync-models.out /var/log/veles/sync-models.err
      /bin/chmod 0644 /var/log/veles/sync-models.out /var/log/veles/sync-models.err
    '';
  };
}
