import hashlib
from pathlib import Path
import tempfile
import unittest

try:
    import mujoco
    import numpy as np
    from multiros.viewer import load_snapshot, load_model, update_display_state
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

    def test_binary_model_embeds_assets_without_source_files(self):
        root = Path(self.temp.name)
        mesh = root / 'tetra.obj'
        mesh.write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nv 0 0 1\n'
                        'f 1 3 2\nf 1 2 4\nf 1 4 3\nf 2 3 4\n')
        scene = root / 'scene.xml'
        scene.write_text('<mujoco><asset><mesh name="tetra" file="tetra.obj"/></asset>'
                         '<worldbody><geom type="mesh" mesh="tetra"/></worldbody></mujoco>')
        model = load_model(scene)
        binary = root / 'scene.mjb'
        mujoco.mj_saveModel(model, str(binary))
        mesh.unlink()
        scene.unlink()
        restored = load_model(binary)
        np.testing.assert_array_equal(restored.mesh_vert, model.mesh_vert)
        np.testing.assert_array_equal(restored.mesh_face, model.mesh_face)

    def test_display_kinematics_matches_full_forward_without_sensor_work(self):
        model = mujoco.MjModel.from_xml_string(
            '<mujoco><worldbody><body><joint type="slide" axis="1 0 0"/>'
            '<geom size=".1"/><camera name="camera" pos="0 0 1"/>'
            '<light pos="0 0 2"/><site name="site"/></body></worldbody>'
            '<sensor><framepos objtype="site" objname="site"/></sensor></mujoco>')
        full, display = mujoco.MjData(model), mujoco.MjData(model)
        for position in (.2, -.4):
            full.qpos[0] = display.qpos[0] = position
            display.sensordata[:] = 123
            mujoco.mj_forward(model, full)
            update_display_state(model, display, kinematics_only=True)
            for field in ('xpos', 'xmat', 'geom_xpos', 'geom_xmat', 'cam_xpos',
                          'cam_xmat', 'light_xpos', 'light_xdir', 'subtree_com'):
                np.testing.assert_allclose(getattr(display, field), getattr(full, field), atol=1e-12)
            np.testing.assert_array_equal(display.sensordata, 123)

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
