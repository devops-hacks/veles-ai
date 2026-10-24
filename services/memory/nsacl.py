"""Namespace access-control decisions for the OpenViking gateway.

Implements the two-level ACL from Chapter 14 of the architecture document:

- ``viking://users/{principal}/...``  owner-only (private namespace);
- ``viking://family/...``             household reads and writes; delete is
                                      guardian-only (30-day trash, Ch. 14);
- ``viking://system/...``             no consumer access at all - the
                                      append-only audit log is written by the
                                      gateway itself.

Posture summary: the family root is the read-shared area; personal
namespaces stay write-private (owner-only). Pure function, no I/O - the
gateway wires ``services/memory/namespaces.example.yaml`` into the
``household`` and ``guardian`` arguments. Deny-by-default: anything not
matching a rule below is refused.
"""

SCHEME = "viking://"
OPS = ("read", "write", "delete")


class AclError(ValueError):
    """Malformed input (bad path or op) - a 4xx for the gateway, not a denial."""


def _segments(path: str) -> list[str]:
    """Split a viking:// URI into path segments, rejecting bad input."""
    if not path.startswith(SCHEME):
        raise AclError(f"path must start with {SCHEME!r}: {path!r}")
    segments = [s for s in path[len(SCHEME) :].split("/") if s]
    if not segments:
        raise AclError("empty viking path")
    return segments


def check(
    op: str,
    path: str,
    principal: str,
    household: set[str],
    guardian: str,
) -> bool:
    """Return True when ``principal`` may perform ``op`` on ``path``.

    Rules (Chapter 14, two-level ACL):

    - Unknown principals are always denied; A1 gateway keys map to a
      principal before this function runs.
    - ``users/{owner}/...``: only the owner, all three ops. ``delete`` here
      is the soft-delete-to-trash; purge stays guardian-side.
    - ``family/...``: every household member reads and writes; ``delete``
      is guardian-only.
    - ``system/...`` and any other root: denied - the audit log and future
      system roots are gateway-managed.
    - Segment-boundary matching: ``users/alice-notes`` is NOT ``users/alice``.
    """
    if op not in OPS:
        raise AclError(f"op must be one of {OPS!r}: {op!r}")
    if not principal or principal not in household:
        return False
    segments = _segments(path)
    root, tail = segments[0], segments[1:]

    if root == "users":
        if len(tail) < 1:
            return False  # /users/ itself is not an addressable store
        return principal == tail[0]

    if root == "family":
        if op == "delete":
            return principal == guardian  # guardian-only, Ch. 14
        return True  # read-shared / write-private cohort area

    return False  # system/* and unknown roots: deny by default
