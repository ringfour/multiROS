"""Compare native GL rendering and snapshot transport without stepping physics."""
import argparse
import ctypes
import json
from pathlib import Path
import platform
import time

import glfw
import mujoco
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--track-body', default='chassis')
    parser.add_argument('--frames', type=int, default=60)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    args = parser.parse_args()
    if min(args.frames, args.width, args.height) <= 0:
        parser.error('frames and dimensions must be positive')
    scene_path = args.model or args.runtime / 'scene.xml'
    model = (mujoco.MjModel.from_binary_path(str(scene_path)) if scene_path.suffix == '.mjb'
             else mujoco.MjModel.from_xml_path(str(scene_path)))
    data = mujoco.MjData(model)
    samples = []
    for _ in range(args.frames):
        start = time.perf_counter()
        with np.load(args.runtime / 'viewer.npz', allow_pickle=False) as state:
            for name in ('qpos', 'qvel', 'ctrl'):
                getattr(data, name)[:] = state[name]
            data.time = float(state['time'])
        samples.append((time.perf_counter() - start) * 1000)
    mujoco.mj_forward(model, data)
    if not glfw.init():
        raise RuntimeError('GLFW initialization failed')
    window = None
    context = None
    try:
        glfw.window_hint(glfw.VISIBLE, False)
        window = glfw.create_window(args.width, args.height, 'MuJoCo benchmark', None, None)
        if not window:
            raise RuntimeError('GLFW window creation failed')
        glfw.make_context_current(window)
        glfw.swap_interval(0)
        get_string = ctypes.CFUNCTYPE(ctypes.c_char_p, ctypes.c_uint)(glfw.get_proc_address('glGetString'))
        finish = ctypes.CFUNCTYPE(None)(glfw.get_proc_address('glFinish'))
        scene = mujoco.MjvScene(model, maxgeom=10000)
        context = mujoco.MjrContext(model, mujoco.mjtFontScale.mjFONTSCALE_100)
        option = mujoco.MjvOption()
        option.geomgroup[2], option.geomgroup[3] = 1, 0
        camera = mujoco.MjvCamera()
        camera.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        camera.trackbodyid = model.body(args.track_body).id
        camera.distance, camera.azimuth, camera.elevation = 3, 120, -20
        viewport = mujoco.MjrRect(0, 0, args.width, args.height)
        for flag in (mujoco.mjtRndFlag.mjRND_SHADOW, mujoco.mjtRndFlag.mjRND_REFLECTION):
            scene.flags[flag] = 0
        def frame():
            mujoco.mjv_updateScene(model, data, option, None, camera, mujoco.mjtCatBit.mjCAT_ALL, scene)
            mujoco.mjr_render(viewport, scene, context)
            finish()
        for _ in range(5):
            frame()
        render = []
        for _ in range(args.frames):
            start = time.perf_counter()
            frame()
            render.append((time.perf_counter() - start) * 1000)
        def stats(values):
            return {key: round(float(value), 3) for key, value in
                    [('median_ms', np.median(values)), ('p95_ms', np.percentile(values, 95))]}
        print(json.dumps(dict(host=platform.system(), mujoco=mujoco.__version__,
                              renderer=get_string(0x1F01).decode(),
                              gl_version=get_string(0x1F02).decode(),
                              viewport=[args.width, args.height], effects=False,
                              mesh_triangles=model.nmeshface, frames=args.frames,
                              snapshot=stats(samples), render=stats(render)), indent=2), flush=True)
    finally:
        if context is not None:
            context.free()
        if window is not None:
            glfw.destroy_window(window)
        glfw.terminate()


if __name__ == '__main__':
    main()
