import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from multiros.cli import init_robot, load_config, plan, revision, select_backend


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="robot space ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for file in ("compose.yaml", "lighter.yaml"):
            (self.root / file).write_text("services: {}\n")
        self.config = {"schema": 1, "project": "robot-one", "compose": ["compose.yaml"],
                       "backends": {"lighter": ["lighter.yaml"]},
                       "entrypoint": ["/entrypoint"], "commands": {
                           "sim": {"where": "container", "argv": ["launch", "robot"]},
                           "view": {"where": "host", "argv": ["{python}", "{root}/viewer.py"]}}}

    def test_robot_arguments_are_literal_and_paths_with_spaces_stay_single(self):
        args = ["name:=hello world", "$(touch /tmp/should-not-exist)", "`whoami`"]
        command = plan(self.config, self.root, "lighter", "sim", args)
        self.assertEqual(command[-5:], ["launch", "robot", *args])
        self.assertIn(str(self.root / "compose.yaml"), command)
        self.assertIn(str(self.root / "lighter.yaml"), command)
        self.assertIn("/entrypoint", command)

    def test_down_is_project_scoped_and_preserves_volumes(self):
        command = plan(self.config, self.root, "default", "down", [])
        self.assertEqual(command[-1], "stop")
        self.assertEqual(command[command.index("--project-name") + 1], "robot-one")
        with self.assertRaises(ValueError):
            plan(self.config, self.root, "default", "down", ["--volumes"])

    def test_host_frontend_never_goes_through_container(self):
        command = plan(self.config, self.root, "default", "view", [])
        self.assertNotIn("docker", command)
        self.assertEqual(command[-1], str(self.root / "viewer.py"))

    def test_missing_backend_does_not_silently_fall_back(self):
        with self.assertRaisesRegex(ValueError, "not configured"):
            plan(self.config, self.root, "nvidia", "sim", [])

    def test_no_gpu_inference_from_host_os(self):
        self.assertEqual(select_backend("auto", "lighter"), "lighter")
        self.assertEqual(select_backend("auto", "remote-linux"), "default")
        self.assertEqual(select_backend("cpu", "lighter"), "cpu")

    def test_source_outside_git_is_not_reported_as_parent_repository(self):
        with patch("multiros.cli.capture", return_value=str(self.root.parent)):
            self.assertIsNone(revision(self.root)["revision"])

    def test_config_rejects_bad_schema_and_project(self):
        path = self.root / "multiros.json"
        path.write_text(json.dumps({**self.config, "schema": 2}))
        with self.assertRaises(ValueError):
            load_config(path)
        path.write_text(json.dumps({**self.config, "project": "$(bad)"}))
        with self.assertRaises(ValueError):
            load_config(path)

    def test_starter_refuses_overwrites_before_writing_anything(self):
        destination = self.root / "new robot"
        destination.mkdir()
        (destination / "pixi.toml").write_text("existing project")
        with self.assertRaisesRegex(ValueError, "Refusing to overwrite"):
            init_robot(destination)
        self.assertEqual(list(destination.iterdir()), [destination / "pixi.toml"])
        self.assertEqual((destination / "pixi.toml").read_text(), "existing project")


if __name__ == "__main__":
    unittest.main()
