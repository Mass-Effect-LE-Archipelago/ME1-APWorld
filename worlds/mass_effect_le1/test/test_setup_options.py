import pathlib
import sys
import unittest


def setup_tools() -> pathlib.Path | None:
    """APWorldMaker/tools/setup, from this world's source folder or its vendored copy (None in a packaged .apworld)."""
    for parent in pathlib.Path(__file__).resolve().parents:
        candidate = parent / "tools" / "setup" / "export_options.py"
        if candidate.exists():
            return candidate.parent
    return None


class TestSetupOptions(unittest.TestCase):
    def test_setup_options_json_matches_world(self) -> None:
        tools = setup_tools()
        if tools is None:
            self.skipTest("tools/setup not beside this world (packaged .apworld)")
        sys.path.insert(0, str(tools))
        try:
            from export_options import options_json
        finally:
            sys.path.remove(str(tools))
        self.assertEqual((tools / "options-me1.json").read_text(encoding="utf-8"), options_json(),
                         "run tools/setup/export_options.py to refresh options-me1.json")

    def test_me2_options_copy_is_current(self) -> None:
        tools = setup_tools()
        me2 = tools and tools.parents[1] / "ME2-LE-Archipelago" / "tools" / "setup" / "options.json"
        if not me2 or not me2.exists():
            self.skipTest("ME2-LE-Archipelago not beside tools/setup")
        self.assertEqual((tools / "options-me2.json").read_bytes(), me2.read_bytes(),
                         "copy ME2-LE-Archipelago/tools/setup/options.json to tools/setup/options-me2.json")
