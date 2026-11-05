#!/usr/bin/env python3
"""Isolate MuJoCo render features without robot assets or a physics process."""
import argparse
import os
import time

os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from OpenGL import GL

parser = argparse.ArgumentParser()
parser.add_argument('case', choices=['plain', 'texture', 'skybox', 'reflection', 'lights', 'fog', 'transparency', 'combined'])
parser.add_argument('--frames', type=int, default=5)
args = parser.parse_args()
case = args.case
assets = ''
material = ''
extra = ''
visual = ''
if case in ('texture', 'reflection', 'combined'):
    assets += '<texture name="checker" type="2d" builtin="checker" width="64" height="64" rgb1=".8 .2 .1" rgb2=".1 .3 .8"/>'
    assets += f'<material name="surface" texture="checker" reflectance="{.2 if case in ("reflection", "combined") else 0}"/>'
    material = 'material="surface"'
if case in ('skybox', 'combined'):
    assets += '<texture type="skybox" builtin="gradient" rgb1=".3 .5 .7" rgb2="0 0 0" width="64" height="384"/>'
if case in ('lights', 'combined'):
    extra += '<light pos="1 1 1" dir="-1 -1 -2" diffuse=".5 .5 .5"/>'
if case == 'fog':
    visual = '<map fogstart=".1" fogend="3"/>'
alpha = '.5' if case == 'transparency' else '1'
xml = f'''<mujoco><visual><global offwidth="320" offheight="240"/>{visual}</visual>
<asset>{assets}</asset><worldbody>
<light pos="0 0 1" dir="0 0 -1"/>{extra}
<camera name="rgbd" pos="0 0 0" fovy="60"/>
<geom name="wall" type="box" size="4 4 .01" pos="0 0 -2" rgba=".8 .3 .2 1" {material}/>
<geom name="ball" type="sphere" size=".2" pos="-.4 0 -1.2" rgba=".2 .8 .2 {alpha}"/>
</worldbody></mujoco>'''
print('CASE', case, flush=True)
model = mujoco.MjModel.from_xml_string(xml)
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)
with mujoco.Renderer(model, height=240, width=320) as renderer:
    print('GL', GL.glGetString(GL.GL_RENDERER).decode(), flush=True)
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
    assert abs(float(depth[120, 160]) - 1.99) < .01
    assert segmentation[120, 160, 0] == model.geom('wall').id
    assert np.isfinite(depth).all()
    print('PASS', case, 'rgb_mean', float(rgb.mean()), 'depth', float(depth[120, 160]),
          'fps', args.frames / (time.monotonic() - started), flush=True)
