"""Single-threaded, read-only MuJoCo viewer with caller-controlled draw rate."""
from contextlib import nullcontext

import glfw
import mujoco
import numpy as np


class GlfwViewer:
    def __init__(self, model, data, *, width=1280, height=720, visible=True, pose_tolerance=1e-5):
        self.model, self.data = model, data
        self.window = None
        self.context = None
        self.frames = 0
        self.idle_frames = 0
        self.pose_tolerance = pose_tolerance
        self._last_pose = None
        self._dirty = True
        if not glfw.init():
            raise RuntimeError('GLFW initialization failed')
        try:
            glfw.window_hint(glfw.VISIBLE, visible)
            self.window = glfw.create_window(width, height, 'multiROS', None, None)
            if self.window is None:
                raise RuntimeError('GLFW window creation failed')
            glfw.make_context_current(self.window)
            # main() budgets the entire frame; vsync is not our frame limiter.
            glfw.swap_interval(0)
            self.context = mujoco.MjrContext(model, mujoco.mjtFontScale.mjFONTSCALE_100)
            mujoco.mjr_setBuffer(mujoco.mjtFramebuffer.mjFB_WINDOW, self.context)
            self.cam = mujoco.MjvCamera()
            mujoco.mjv_defaultFreeCamera(model, self.cam)
            self.opt = mujoco.MjvOption()
            self.user_scn = mujoco.MjvScene(model, maxgeom=10000)
            self.cursor = glfw.get_cursor_pos(self.window)
            glfw.set_cursor_pos_callback(self.window, self._move)
            glfw.set_mouse_button_callback(self.window, self._button)
            glfw.set_scroll_callback(self.window, self._scroll)
            glfw.set_key_callback(self.window, self._key)
            glfw.set_window_refresh_callback(self.window, self._refresh)
            glfw.set_framebuffer_size_callback(self.window, self._resize)
        except Exception:
            self.close()
            raise

    def lock(self):
        return nullcontext()

    def is_running(self):
        return self.window is not None and not glfw.window_should_close(self.window)

    def _button(self, window, button, action, mods):
        self.cursor = glfw.get_cursor_pos(window)

    def _move(self, window, x, y):
        previous = self.cursor
        self.cursor = x, y
        width, height = glfw.get_window_size(window)
        if height <= 0:
            return
        shift = any(glfw.get_key(window, key) == glfw.PRESS
                    for key in (glfw.KEY_LEFT_SHIFT, glfw.KEY_RIGHT_SHIFT))
        if glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_RIGHT) == glfw.PRESS:
            action = mujoco.mjtMouse.mjMOUSE_MOVE_H if shift else mujoco.mjtMouse.mjMOUSE_MOVE_V
        elif glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_LEFT) == glfw.PRESS:
            action = mujoco.mjtMouse.mjMOUSE_ROTATE_H if shift else mujoco.mjtMouse.mjMOUSE_ROTATE_V
        elif glfw.get_mouse_button(window, glfw.MOUSE_BUTTON_MIDDLE) == glfw.PRESS:
            action = mujoco.mjtMouse.mjMOUSE_ZOOM
        else:
            return
        self._dirty = True
        self._move_camera(action, (x-previous[0])/height, (y-previous[1])/height)

    def _scroll(self, window, x, y):
        self._dirty = True
        self._move_camera(mujoco.mjtMouse.mjMOUSE_ZOOM, 0., .05*y)

    def _move_camera(self, action, dx, dy):
        # Use the public API shared by the supported MuJoCo 3.12/3.13 builds.
        mujoco.mjv_moveCamera(self.model, action, dx, dy, self.cam)

    def _refresh(self, window):
        self._dirty = True

    def _resize(self, window, width, height):
        self._dirty = True

    def _key(self, window, key, scancode, action, mods):
        if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
            glfw.set_window_should_close(window, True)

    def _visual_pose(self):
        visible = ((self.model.geom_rgba[:, 3] > 0)
                   & (self.opt.geomgroup[self.model.geom_group] != 0))
        parts = [self.opt.geomgroup, self.data.geom_xpos[visible].ravel(),
                 self.data.geom_xmat[visible].ravel(), self.data.light_xpos.ravel(),
                 self.data.light_xdir.ravel()]
        if self.cam.type == mujoco.mjtCamera.mjCAMERA_TRACKING:
            parts.append(self.data.xpos[self.cam.trackbodyid])
        if self.cam.type == mujoco.mjtCamera.mjCAMERA_FIXED:
            parts.extend([self.data.cam_xpos[self.cam.fixedcamid],
                          self.data.cam_xmat[self.cam.fixedcamid]])
        return np.concatenate(parts)

    def sync(self):
        glfw.poll_events()
        width, height = glfw.get_framebuffer_size(self.window)
        # Minimized windows do not submit a scene to the GPU.
        if width <= 0 or height <= 0 or glfw.get_window_attrib(self.window, glfw.ICONIFIED):
            return
        pose = self._visual_pose()
        # Deformable geometry needs more than rigid geom poses to detect motion.
        reusable = not self.model.nflex and not self.model.nskin
        if (reusable and not self._dirty and self._last_pose is not None
                and pose.shape == self._last_pose.shape
                and np.allclose(pose, self._last_pose, rtol=0., atol=self.pose_tolerance)):
            self.idle_frames += 1
            return
        glfw.make_context_current(self.window)
        mujoco.mjv_updateScene(self.model, self.data, self.opt, None, self.cam,
                              mujoco.mjtCatBit.mjCAT_ALL, self.user_scn)
        mujoco.mjr_render(mujoco.MjrRect(0, 0, width, height), self.user_scn, self.context)
        glfw.swap_buffers(self.window)
        self.frames += 1
        self._last_pose = pose
        self._dirty = False

    def close(self):
        if self.window is not None:
            glfw.make_context_current(self.window)
        if self.context is not None:
            self.context.free()
            self.context = None
        if self.window is not None:
            glfw.destroy_window(self.window)
            self.window = None
        glfw.terminate()
