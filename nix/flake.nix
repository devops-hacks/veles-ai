# nix/flake.nix - darwin host declaration (converged, 1b-i)
# next switch: nix run nix-darwin -- switch --flake .#mac-ai
{
  description = "veles-ai: declarative inference + gateway host (code name Veles AI)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nix-darwin.url = "github:nix-darwin/nix-darwin";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    sops-nix.url = "github:Mic92/sops-nix";
    sops-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs@{ self, nix-darwin, nixpkgs, sops-nix }:
    {
      darwinConfigurations.mac-ai = nix-darwin.lib.darwinSystem {
        modules = [
        sops-nix.darwinModules.sops
        ({ pkgs, config, ... }: {
          nixpkgs.hostPlatform = "aarch64-darwin";

          networking.hostName = "mac-ai";

          # ---- A1 amendment: gateway keys are sops-managed ----
          # sops.secrets."llama_swap/key_operator" = { };
          # sops.secrets."llama_swap/key_family"   = { };
          # sops.secrets."llama_swap/key_agents"   = { };

          # ---- operator's editor/container stack (converged via brew) ----
          # PARKED: homebrew/primaryUser deferred pending architect ruling on
          # PII policy + homebrew egress rows (current nix-darwin requires
          # system.primaryUser once homebrew.enable is set).
          # homebrew = {
          #   enable = true;
          #   casks = [ "orbstack" ];
          #   onActivation.cleanup = "none";  # removals are PRs, never automatic
          # };

          # ---- router: llama-swap as a kept-alive launchd service ----
          # PARKED: wired in the inference phase (roadmap PR 3); /run/* paths
          # are Linux-isms - real macOS paths decided then.
          # launchd.user.services.llama-swap = {
          #   serviceConfig = {
          #     ProgramArguments = [
          #       "llama-swap"
          #       "-config" "/run/llama-swap/config.yml"
          #       "-listen" "127.0.0.1:4002"
          #     ];
          #     KeepAlive = true;
          #     RunAtLoad = true;
          #     # EnvironmentVariables.LLAMA_SWAP_KEY = "@sopsKey@";
          #   };
          # };

          # ---- nightly GGUF sync (manifest -> disk -> swap config) ----
          # PARKED: wired in the inference phase (roadmap PR 3); /run/* paths
          # are Linux-isms - real macOS paths decided then.
          # launchd.user.services.sync-models = {
          #   serviceConfig = {
          #     Program = "/run/current-system/sw/bin/sync-models";
          #     StartCalendarInterval = [{ Hour = 3; Minute = 30; }];
          #   };
          # };

          # ---- A6: offline posture ----
          # TODO: /etc/hosts alias "ai.lan" -> LAN IP so the family PWA
          # works when the tailnet control plane is unreachable

          environment.systemPackages = with pkgs;
            [ git gh just jq yq ];

          # TODO: enable Remote Login (SSH) for VS Code Remote-SSH:
          # system.defaults + services.openssh.enable = true;
          # enable only with key-only auth when A1 provisions gateway keys
          # (see PR 6 secrets).

          system.stateVersion = 5;
        })
      ];
      };
    };
}
