"""Contract tests for the Chapter 14 two-level namespace ACL.

This module is the worked TDD example the start guide points at
(docs/vscode-start-guide.md section 5): read these tests first - the names
are the spec - then extend nsacl.py via the same red-green loop. Your
first PR adds ``visible_roots()`` the same way.
"""

import pytest

from services.memory.nsacl import AclError, check, visible_roots

HOUSEHOLD = {"alice", "ben", "claire"}
GUARDIAN = "alice"


class TestUsersNamespace:
    """viking://users/{principal}/ - owner-only, all operations."""

    def test_owner_read(self):
        assert check("read", "viking://users/alice/prefs", "alice", HOUSEHOLD, GUARDIAN)

    def test_owner_write(self):
        assert check("write", "viking://users/alice/journal", "alice", HOUSEHOLD, GUARDIAN)

    def test_owner_soft_delete(self):
        # delete = soft-delete to trash; the purge is guardian-side, Ch. 14
        assert check("delete", "viking://users/alice/journal/old", "alice", HOUSEHOLD, GUARDIAN)

    def test_cross_user_read_denied(self):
        assert not check("read", "viking://users/alice/prefs", "ben", HOUSEHOLD, GUARDIAN)

    def test_cross_user_write_denied(self):
        assert not check("write", "viking://users/alice/prefs", "ben", HOUSEHOLD, GUARDIAN)

    def test_segment_boundary_denied(self):
        # 'alice-notes' is a different principal - never prefix-match (A2)
        assert not check("read", "viking://users/alice-notes/x", "alice", HOUSEHOLD, GUARDIAN)

    def test_users_root_not_addressable(self):
        assert not check("read", "viking://users", "alice", HOUSEHOLD, GUARDIAN)


class TestFamilyNamespace:
    """viking://family/ - household reads and writes, guardian-only delete."""

    def test_member_read(self):
        assert check("read", "viking://family/status/board", "ben", HOUSEHOLD, GUARDIAN)

    def test_member_write(self):
        # read-shared / write-private cohort: family areas take member writes
        assert check("write", "viking://family/bau/cards", "claire", HOUSEHOLD, GUARDIAN)

    def test_member_delete_denied(self):
        assert not check("delete", "viking://family/status/board", "ben", HOUSEHOLD, GUARDIAN)

    def test_guardian_delete_allowed(self):
        assert check("delete", "viking://family/status/board", "alice", HOUSEHOLD, GUARDIAN)


class TestDenyByDefault:
    """Anything not matching a rule is refused - the no-back-door property."""

    def test_system_prefix_denied_even_for_guardian(self):
        for op in ("read", "write", "delete"):
            assert not check(op, "viking://system/audit/log.jsonl", "alice", HOUSEHOLD, GUARDIAN)

    def test_unknown_root_denied(self):
        assert not check("read", "viking://shared/everything", "alice", HOUSEHOLD, GUARDIAN)

    def test_unknown_principal_denied(self):
        assert not check("read", "viking://family/status", "mallory", HOUSEHOLD, GUARDIAN)

    def test_empty_principal_denied(self):
        assert not check("read", "viking://family/status", "", HOUSEHOLD, GUARDIAN)


class TestMalformedInput:
    """Bad paths/ops are 4xx material (AclError), never a silent denial."""

    def test_non_viking_scheme_raises(self):
        with pytest.raises(AclError):
            check("read", "https://family/status", "alice", HOUSEHOLD, GUARDIAN)

    def test_empty_path_raises(self):
        with pytest.raises(AclError):
            check("read", "viking://", "alice", HOUSEHOLD, GUARDIAN)

    def test_bad_op_raises(self):
        with pytest.raises(AclError):
            check("admin", "viking://family/status", "alice", HOUSEHOLD, GUARDIAN)


class TestVisibleRoots:
    """Which roots may this principal read? (Ch. 14, Listing 14-3)"""

    def test_visible_roots_own_plus_family(self):
        assert visible_roots("ben", HOUSEHOLD, GUARDIAN) == [
            "viking://users/ben/",
            "viking://family/",
        ]

    def test_visible_roots_unknown_principal_is_empty(self):
        assert visible_roots("mallory", HOUSEHOLD, GUARDIAN) == []

    def test_visible_roots_empty_principal_is_empty(self):
        assert visible_roots("", HOUSEHOLD, GUARDIAN) == []
