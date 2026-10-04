import tempfile
import unittest
from pathlib import Path

from bridgekeeper import (
    BridgekeeperError,
    add_authority,
    add_supersedes,
    add_transition,
    add_unresolved,
    audit,
    load,
    new_handoff,
    render_markdown,
    render_mermaid,
    save,
    set_canonical,
)


class BridgekeeperTests(unittest.TestCase):
    def test_canonical_is_explicit_and_authority_linked(self):
        data = new_handoff("Project", "bridge-002")
        add_authority(data, "A001", "Spec", "spec:current", "specification")
        set_canonical(data, "mode", "current", ["A001"], "Declared state.")
        self.assertEqual(data["canonical"][0]["value"], "current")
        self.assertEqual(data["canonical"][0]["authorities"], ["A001"])
        self.assertEqual(audit(data), [])

    def test_change_and_correction_remain_distinct(self):
        data = new_handoff("Project", "bridge-002")
        add_authority(data, "A001", "Commit", "git:abc", "commit")
        add_transition(data, "changes", "layout", "v1", "v2", "Design evolved.", ["A001"])
        add_transition(data, "corrections", "date", "1904", "1903", "Transcription corrected.", ["A001"])
        self.assertEqual(len(data["changes"]), 1)
        self.assertEqual(len(data["corrections"]), 1)

    def test_self_supersession_is_rejected(self):
        data = new_handoff("Project", "bridge-002")
        with self.assertRaises(BridgekeeperError):
            add_supersedes(data, "bridge-002")

    def test_unresolved_without_reopen_condition_is_flagged(self):
        data = new_handoff("Project", "bridge-002")
        add_unresolved(data, "identity", "Identity remains unknown.")
        self.assertTrue(any("no reopen condition" in item for item in audit(data)))

    def test_round_trip_and_renderers(self):
        data = new_handoff("Project", "bridge-002")
        add_authority(data, "A001", "Ledger item", "evidence-ledger:E004", "tool-record")
        set_canonical(data, "date", 1903, ["A001"])
        add_supersedes(data, "bridge-001")
        add_unresolved(data, "identity", "Witness identity remains unknown.", reopen_when="Named primary source found.")

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "handoff.json"
            save(path, data)
            loaded = load(path)

        self.assertIn("bridge-002", render_markdown(loaded))
        self.assertIn("superseded by", render_mermaid(loaded))


if __name__ == "__main__":
    unittest.main()
