#!/usr/bin/env python3
"""Exit 1 if any secrets/*.yaml argument lacks a top-level sops: key.

A top-level "sops:" block is the proof a file is sops-encrypted
ciphertext; this guard makes plaintext under secrets/ structurally
impossible to commit. Paths outside secrets/ (and non-YAML files) are
ignored. Stdlib only; wired as a local pre-commit hook.
"""

import re
import sys
from pathlib import Path

SECRET_PATTERN = re.compile(r"^secrets/.*\.ya?ml$")


def is_encrypted(path: Path) -> bool:
    """True when the file has a 'sops:' line at column 0 (sops metadata)."""
    for line in path.read_text().splitlines():
        if line.startswith("sops:"):
            return True
    return False


def main(argv: list[str]) -> int:
    offenders = [arg for arg in argv if SECRET_PATTERN.match(arg) and not is_encrypted(Path(arg))]
    if offenders:
        print("plaintext under secrets/ - encrypt with: sops --encrypt --in-place <file>")
        for name in offenders:
            print(name)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
