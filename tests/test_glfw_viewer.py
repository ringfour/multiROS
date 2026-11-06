"""Read-only camera controls and visibility-aware redraw invalidation."""
import unittest

try:
    import mujoco
    import numpy as np
    from multiros.glfw_viewer import GlfwViewer
except ImportError:
    mujoco = None


@unittest.skipIf(mujoco is None, 'Viewer dependencies are optional')
class LightweightViewerTests(unittest.TestCase):
    def viewer(self, light=False):
        light_xml = '<light pos="1 0 1"/>' if light else ''
        model = mujoco.MjModel.from_xml_string(f'''<mujoco><worldbody>
          <body><joint name="shown"/><geom group="2" type="box" size=".1 .2 .3"/></body>
          <body pos="1 0 0"><joint name="hidden"/>
            <geom group="3" type="box" size=".1 .2 .3"/>{light_xml}</body>
          </worldbody></mujoco>''')
        viewer = GlfwViewer.__new__(GlfwViewer)
        viewer.model = model
        viewer.data = mujoco.MjData(model)
        viewer.opt = mujoco.MjvOption()
        viewer.opt.geomgroup[3] = 0
        viewer.cam = mujoco.MjvCamera()
        mujoco.mjv_defaultFreeCamera(model, viewer.cam)
        mujoco.mj_forward(model, viewer.data)
        return viewer

    def test_hidden_joint_motion_does_not_invalidate_visible_scene(self):
        viewer = self.viewer()
        before = viewer._visual_pose()
        viewer.data.joint('hidden').qpos[0] = .2
        mujoco.mj_forward(viewer.model, viewer.data)
        np.testing.assert_array_equal(before, viewer._visual_pose())
        viewer.data.joint('shown').qpos[0] = .2
        mujoco.mj_forward(viewer.model, viewer.data)
        self.assertFalse(np.array_equal(before, viewer._visual_pose()))

    def test_moving_light_invalidates_scene_even_on_hidden_body(self):
        viewer = self.viewer(light=True)
        before = viewer._visual_pose()
        viewer.data.joint('hidden').qpos[0] = .2
        mujoco.mj_forward(viewer.model, viewer.data)
        self.assertFalse(np.array_equal(before, viewer._visual_pose()))

    def test_camera_controls_use_supported_api_without_changing_physics(self):
        viewer = self.viewer()
        before = viewer.data.qpos.copy()
        distance = viewer.cam.distance
        viewer._scroll(None, 0, 1)
        self.assertLess(viewer.cam.distance, distance)
        azimuth = viewer.cam.azimuth
        viewer._move_camera(mujoco.mjtMouse.mjMOUSE_ROTATE_H, .05, .02)
        self.assertNotEqual(viewer.cam.azimuth, azimuth)
        np.testing.assert_array_equal(viewer.data.qpos, before)


if __name__ == '__main__':
    unittest.main()
