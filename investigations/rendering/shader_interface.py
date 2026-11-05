#!/usr/bin/env python3
"""Control: an ordinary linked GLSL program using xy and w passes even before the fix."""
import os
os.environ.setdefault('MUJOCO_GL', 'egl')
import mujoco
import numpy as np
from OpenGL import GL
from OpenGL.GL.shaders import compileProgram, compileShader

model = mujoco.MjModel.from_xml_string('<mujoco><visual><global offwidth="32" offheight="32"/><quality offsamples="0"/></visual></mujoco>')
with mujoco.Renderer(model, height=32, width=32) as renderer:
    mujoco.mjr_setBuffer(mujoco.mjtFramebuffer.mjFB_OFFSCREEN, renderer._mjr_context)
    program = compileProgram(
        compileShader('''#version 120
varying vec4 value;
void main() { gl_Position = gl_Vertex; value = gl_Vertex; }
''', GL.GL_VERTEX_SHADER),
        compileShader('''#version 120
varying vec4 value;
void main() { gl_FragColor = vec4(value.xy * 0.5 + 0.5, value.w, 1.0); }
''', GL.GL_FRAGMENT_SHADER))
    print('GL', GL.glGetString(GL.GL_RENDERER).decode(), flush=True)
    GL.glViewport(0, 0, 32, 32)
    GL.glDisable(GL.GL_DEPTH_TEST)
    GL.glUseProgram(program)
    GL.glBegin(GL.GL_TRIANGLES)
    for point in [(-1., -1., 0., 1.), (3., -1., 0., 1.), (-1., 3., 0., 1.)]:
        GL.glVertex4f(*point)
    GL.glEnd()
    GL.glFinish()
    pixel = np.frombuffer(GL.glReadPixels(16, 16, 1, 1, GL.GL_RGB, GL.GL_UNSIGNED_BYTE), dtype=np.uint8)
    print('PIXEL', pixel.tolist(), flush=True)
    assert np.allclose(pixel, [131, 131, 255], atol=2), pixel
    assert GL.glGetError() == GL.GL_NO_ERROR
    GL.glUseProgram(0)
    GL.glDeleteProgram(program)
    print('PASS: ordinary linked GLSL preserves xy and w', flush=True)
