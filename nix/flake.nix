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
        ./inference.nix
        ({ pkgs, config, ... }: {
          nixpkgs.hostPlatform = "aarch64-darwin";

          networking.hostName = "mac-ai";

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
