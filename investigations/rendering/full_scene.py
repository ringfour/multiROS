#!/usr/bin/env python3
"""Check a read-only robot scene and snapshot; never run physics or ROS."""
import argparse
import json
import os
from pathlib import Path
import time

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from OpenGL import GL
from PIL import Image

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--runtime', type=Path, default=Path('/workspace/xlerobot/.runtime'))
parser.add_argument('--state', type=Path)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--frames', type=int, default=30)
parser.add_argument('--fast', action='store_true')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
model = mujoco.MjModel.from_xml_path(str(args.runtime / 'scene.xml'))
data = mujoco.MjData(model)
with np.load(args.state or args.runtime / 'physics.npz') as state:
    data.time = float(state['time'])
    for name in ('qpos', 'qvel', 'ctrl'):
        getattr(data, name)[:] = state[name]
mujoco.mj_forward(model, data)
np.savez(args.output / 'state.npz', time=data.time, qpos=data.qpos, qvel=data.qvel, ctrl=data.ctrl)
if args.fast:
    model.vis.quality.offsamples = 0
option = mujoco.MjvOption()
option.geomgroup[3] = 0
with mujoco.Renderer(model, height=480, width=640) as renderer:
    device = GL.glGetString(GL.GL_RENDERER).decode()
    print('GL', device, 'geometries', model.ngeom, 'meshes', model.nmesh, flush=True)
    timings = []
    for frame in range(args.frames):
        started = time.monotonic()
        renderer.update_scene(data, camera='rgbd', scene_option=option)
        if args.fast:
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_SHADOW] = False
            renderer.scene.flags[mujoco.mjtRndFlag.mjRND_REFLECTION] = False
        rgb = renderer.render().copy()
        renderer.enable_depth_rendering()
        depth = renderer.render().copy()
        renderer.disable_depth_rendering()
        renderer.enable_segmentation_rendering()
        segmentation = renderer.render().copy()
        renderer.disable_segmentation_rendering()
        timings.append(time.monotonic() - started)
        print('frame', frame, 'seconds', round(timings[-1], 4), flush=True)
    cam = model.camera('rgbd').id
    direction = -data.cam_xmat[cam].reshape(3, 3)[:, 2].copy()
    geom = np.array([-1], dtype=np.int32)
    ray_depth = mujoco.mj_ray(model, data, data.cam_xpos[cam], direction,
                             option.geomgroup, 1, model.body('head_camera_link').id, geom)
    pixel_depth = float(depth[240, 320])
    assert ray_depth > 0 and abs(pixel_depth - ray_depth) < .03, (pixel_depth, ray_depth)
    assert np.isfinite(depth).all()
    assert rgb.shape == (480, 640, 3) and np.std(rgb) > 1
    assert np.any(segmentation[:, :, 0] >= 0)
    assert GL.glGetError() == GL.GL_NO_ERROR
    Image.fromarray(rgb).save(args.output / 'rgb.png')
    Image.fromarray(np.uint8(np.clip(depth, 0, 8) * 255 / 8)).save(args.output / 'depth.png')
    np.savez(args.output / 'pixels.npz', rgb=rgb, depth=depth, segmentation=segmentation)
    warmed = timings[1:] or timings
    result = {'renderer': device, 'geometries': model.ngeom, 'meshes': model.nmesh,
              'frames': args.frames, 'fast': args.fast, 'sim_time': data.time,
              'pixel_depth': pixel_depth, 'ray_depth': float(ray_depth),
              'warm_fps': len(warmed) / sum(warmed), 'first_frame_seconds': timings[0]}
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('PASS', json.dumps(result), flush=True)
