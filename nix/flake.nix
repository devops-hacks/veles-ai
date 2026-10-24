# nix/flake.nix - darwin host declaration (PR 1 skeleton)
# TODO: replace <placeholders>; `darwin-rebuild switch --flake .#mac-ai`
{
  description = "veles-ai: declarative inference + gateway host (code name Veles AI)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    nix-darwin.url = "github:LnL7/nix-darwin";
    nix-darwin.inputs.nixpkgs.follows = "nixpkgs";
    sops-nix.url = "github:Mic92/sops-nix";
    sops-nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = inputs@{ self, nix-darwin, nixpkgs, sops-nix }:
    nix-darwin.lib.darwinSystem {
      system = "aarch64-darwin";
      modules = [
        sops-nix.darwinModules.sops
        ({ pkgs, config, ... }: {
          # TODO: hosts.mac-ai = your Mac's hostname
          networking.hostName = "mac-ai";

          # ---- A1 amendment: gateway keys are sops-managed ----
          # sops.secrets."llama_swap/key_operator" = { };
          # sops.secrets."llama_swap/key_family"   = { };
          # sops.secrets."llama_swap/key_agents"   = { };

          # ---- router: llama-swap as a kept-alive launchd service ----
          launchd.user.services.llama-swap = {
            serviceConfig = {
              # TODO: point at your llama-swap binary + generated config
              ProgramArguments = [
                "${pkgs.llama-swap or pkgs.llama-cpp}/bin/llama-swap"
                "-config" "/run/llama-swap/config.yml"
                "-listen" "127.0.0.1:4002"
              ];
              KeepAlive = true;
              RunAtLoad = true;
              # EnvironmentVariables.LLAMA_SWAP_KEY = "@sopsKey@";
            };
          };

          # ---- nightly GGUF sync (manifest -> disk -> swap config) ----
          launchd.user.services.sync-models = {
            serviceConfig = {
              Program = "/run/current-system/sw/bin/sync-models";
              StartCalendarInterval = [{ Hour = 3; Minute = 30; }];
            };
          };

          # ---- A6: offline posture ----
          # TODO: /etc/hosts alias "ai.lan" -> LAN IP so the family PWA
          # works when the tailnet control plane is unreachable

          environment.systemPackages = with pkgs;
            [ git gh llama-cpp just jq yq ];

          # TODO: enable Remote Login (SSH) for VS Code Remote-SSH:
          # system.defaults + services.openssh.enable = true;

          system.stateVersion = 5;
        })
      ];
    };
}
