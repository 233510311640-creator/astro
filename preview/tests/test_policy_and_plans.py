from pathlib import Path
import tempfile
import unittest

from local_assistant.audit import AuditStore
from local_assistant.app import is_graphic_execution_command, parse_selection
from local_assistant.config import Settings
from local_assistant.file_organizer import GraphicOrganizer
from local_assistant.models import Candidate
from local_assistant.policy import PolicyEngine, PolicyViolation


def make_system(tmp_path: Path):
    home = tmp_path / "home"
    desktop = home / "Desktop"
    desktop.mkdir(parents=True)
    settings = Settings(
        home=home,
        data_dir=tmp_path / "data",
        destination=desktop / "graphic",
        scan_roots=(desktop,),
    )
    policy = PolicyEngine(settings)
    audit = AuditStore(settings.data_dir)
    return settings, policy, GraphicOrganizer(settings, policy, audit)


class PolicyAndPlanTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_plan_never_overwrites_duplicate_names(self):
        settings, _, organizer = make_system(self.root)
        first_dir = settings.scan_roots[0] / "one"
        second_dir = settings.scan_roots[0] / "two"
        first_dir.mkdir()
        second_dir.mkdir()
        first = first_dir / "logo.png"
        second = second_dir / "logo.png"
        first.write_bytes(b"one")
        second.write_bytes(b"two")
        plan = organizer.make_plan(
            [Candidate(first, "Images", "test", 1.0), Candidate(second, "Images", "test", 1.0)]
        )
        destinations = [item.destination for item in plan.items]
        self.assertEqual(len(set(destinations)), 2)
        self.assertEqual(destinations[0].name, "logo.png")
        self.assertEqual(destinations[1].name, "logo (2).png")

    def test_wrong_fingerprint_blocks_move(self):
        settings, _, organizer = make_system(self.root)
        source = settings.scan_roots[0] / "poster.png"
        source.write_bytes(b"image")
        plan = organizer.make_plan([Candidate(source, "Images", "test", 1.0)])
        with self.assertRaises(PolicyViolation):
            organizer.execute(plan, "wrong", settings.data_dir / "STOP")
        self.assertTrue(source.exists())

    def test_move_and_undo(self):
        settings, _, organizer = make_system(self.root)
        source = settings.scan_roots[0] / "poster.png"
        source.write_bytes(b"image")
        plan = organizer.make_plan([Candidate(source, "Images", "test", 1.0)])
        operation_id = organizer.execute(plan, plan.fingerprint, settings.data_dir / "STOP")
        self.assertFalse(source.exists())
        self.assertTrue(plan.items[0].destination.exists())
        self.assertEqual(organizer.undo(operation_id), 1)
        self.assertTrue(source.exists())

    def test_protected_named_ancestor_outside_approved_root_does_not_block_files(self):
        base = self.root / "AppData" / "Local" / "Temp"
        settings, policy, _ = make_system(base)
        source = settings.scan_roots[0] / "poster.png"
        source.write_bytes(b"image")
        policy.assert_scannable(source)

    def test_protected_named_component_inside_approved_root_is_blocked(self):
        settings, policy, _ = make_system(self.root)
        protected = settings.scan_roots[0] / "Windows" / "poster.png"
        protected.parent.mkdir()
        protected.write_bytes(b"image")
        with self.assertRaises(PolicyViolation):
            policy.assert_scannable(protected)

    def test_selection_parser(self):
        self.assertEqual(parse_selection("1,3,5-7", 8), [0, 2, 4, 5, 6])
        self.assertEqual(parse_selection("ALL", 3), [0, 1, 2])
        with self.assertRaises(ValueError):
            parse_selection("0", 3)

    def test_only_explicit_command_activates_graphic_tool(self):
        self.assertTrue(is_graphic_execution_command("/organize-graphics"))
        self.assertTrue(is_graphic_execution_command("  /ORGANIZE-GRAPHICS  "))

    def test_plan_only_request_cannot_activate_graphic_tool(self):
        request = (
            "What is the safest and smartest way to organize my graphic-design files? "
            "Do not scan, move, rename, or change anything. Provide a plan only."
        )
        self.assertFalse(is_graphic_execution_command(request))

    def test_vague_natural_language_cannot_activate_graphic_tool(self):
        self.assertFalse(is_graphic_execution_command("organize my graphic files"))
        self.assertFalse(is_graphic_execution_command("scan for graphic assets"))


if __name__ == "__main__":
    unittest.main()
