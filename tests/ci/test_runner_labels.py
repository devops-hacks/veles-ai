"""Runner labels in CI workflows must be explicit pins, not floating
"latest" aliases (same floating-ref class as unpinned action SHAs).
ubuntu-latest migrates to Ubuntu 26 (actions/runner-images#14748) and
GitHub attaches a migration bulletin notice to every such job; a pinned
label keeps the image choice a deliberate ruling and the annotation
count at zero."""

from pathlib import Path

WF = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def test_runner_labels_no_floating_latest():
    for yml in sorted(WF.glob("*.yml")):
        assert "ubuntu-latest" not in yml.read_text(encoding="utf-8"), yml.name


def test_runner_labels_pinned_to_ubuntu_2404():
    hits = sum(
        yml.read_text(encoding="utf-8").count("runs-on: ubuntu-24.04") for yml in WF.glob("*.yml")
    )
    assert hits == 4, f"expected 4 pinned jobs, found {hits}"
