#!/usr/bin/env python3
"""Check the actual offscreen GL renderer and metric RGB-D output."""
import argparse
import os
import time

os.environ.setdefault('MUJOCO_GL', 'egl')

import mujoco
import numpy as np
from OpenGL import GL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-accelerated', action='store_true')
    parser.add_argument('--frames', type=int, default=20)
    args = parser.parse_args()
    if args.frames < 1:
        parser.error('--frames must be positive')
    model = mujoco.MjModel.from_xml_string('''<mujoco>
      <visual><global offwidth="640" offheight="480"/></visual>
      <asset>
        <texture name="checker" type="2d" builtin="checker" width="64" height="64"
                 rgb1=".8 .2 .1" rgb2=".1 .3 .8"/>
        <material name="surface" texture="checker"/>
      </asset>
      <worldbody>
        <light pos="0 0 1" dir="0 0 -1"/>
        <camera name="rgbd" pos="0 0 0" fovy="60"/>
        <geom name="wall" type="box" size="4 4 .01" pos="0 0 -2"
              rgba=".8 .3 .2 1" material="surface"/>
      </worldbody>
    </mujoco>''')
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    with mujoco.Renderer(model, height=480, width=640) as renderer:
        vendor = GL.glGetString(GL.GL_VENDOR).decode()
        device = GL.glGetString(GL.GL_RENDERER).decode()
        version = GL.glGetString(GL.GL_VERSION).decode()
        print(f'GL vendor: {vendor}\nGL renderer: {device}\nGL version: {version}', flush=True)
        software = any(s in device.lower() for s in ('llvmpipe', 'softpipe', 'swrast', 'software'))
        if args.require_accelerated and software:
            raise AssertionError('Software renderer selected; GPU acceleration is required')
        started = time.monotonic()
        for _ in range(args.frames):
            renderer.update_scene(data, camera='rgbd')
            rgb = renderer.render().copy()
            renderer.enable_depth_rendering()
            depth = renderer.render().copy()
            renderer.disable_depth_rendering()
            renderer.enable_segmentation_rendering()
            segmentation = renderer.render().copy()
            renderer.disable_segmentation_rendering()
        elapsed = time.monotonic() - started
        assert rgb.shape == (480, 640, 3) and rgb.dtype == np.uint8
        assert int(rgb.max()) > int(rgb.min()), 'RGB image is blank'
        center = float(depth[240, 320])
        assert np.isfinite(depth).all(), 'Depth contains non-finite values'
        assert abs(center - 1.99) < .01, f'Expected 1.99 m wall depth, got {center}'
        assert segmentation[240, 320, 0] == model.geom('wall').id
        assert segmentation[240, 320, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
        print(f'RGB, metric depth ({center:.4f} m) and segmentation passed; '
              f'{args.frames / elapsed:.2f} RGB-D+segmentation frames/s at 640x480')


if __name__ == '__main__':
    main()
