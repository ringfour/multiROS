import hashlib
from pathlib import Path
import tempfile
import unittest

try:
    import mujoco
    import numpy as np
    from multiros.viewer import load_snapshot
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, "Run with pixi run -e mujoco test for viewer checks")
class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.npz"
        scene = '<mujoco><worldbody><body><joint/><geom size=".1"/></body></worldbody></mujoco>'
        self.digest = hashlib.sha256(scene.encode()).hexdigest()
        self.model = mujoco.MjModel.from_xml_string(scene)
        self.data = mujoco.MjData(self.model)
        self.state = dict(time=1., qpos=np.array([.5]), qvel=np.array([.1]), ctrl=np.array([]),
                          schema=1, session="test-session", sequence=2,
                          model_sha256=self.digest, mujoco_version=mujoco.__version__)

    def load(self):
        np.savez(self.path, **self.state)
        return load_snapshot(self.path, self.model, self.data, model_digest=self.digest)

    def test_versioned_snapshot_applies_without_stepping(self):
        self.assertEqual(self.load(), ("test-session", 2))
        self.assertEqual(self.data.time, 1.)
        self.assertAlmostEqual(self.data.qpos[0], .5)

    def test_bad_model_or_engine_never_changes_data(self):
        for field in ("model_sha256", "mujoco_version"):
            with self.subTest(field=field):
                old = self.state[field]
                self.state[field] = "wrong"
                with self.assertRaises(ValueError):
                    self.load()
                self.assertEqual(self.data.time, 0.)
                self.assertEqual(self.data.qpos[0], 0.)
                self.state[field] = old

    def test_all_arrays_validated_before_any_mutation(self):
        self.state["qvel"] = np.zeros(2)
        with self.assertRaises(ValueError):
            self.load()
        self.assertEqual(self.data.qpos[0], 0.)
        self.state["qvel"] = np.array([np.nan])
        with self.assertRaises(ValueError):
            self.load()
        self.assertEqual(self.data.time, 0.)

    def test_legacy_requires_explicit_opt_in(self):
        del self.state["schema"]
        with self.assertRaisesRegex(ValueError, "Unversioned"):
            self.load()
        load_snapshot(self.path, self.model, self.data, allow_legacy=True)
        self.assertAlmostEqual(self.data.qpos[0], .5)

    def test_old_sequence_or_different_session_is_rejected_before_mutation(self):
        self.load()
        self.state["qpos"] = np.array([.9])
        for previous in (("test-session", 2), ("old-session", 1)):
            np.savez(self.path, **self.state)
            with self.assertRaises(ValueError):
                load_snapshot(self.path, self.model, self.data,
                              model_digest=self.digest, previous=previous)
            self.assertAlmostEqual(self.data.qpos[0], .5)
