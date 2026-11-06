# MuJoCo texture crash on lighter

This is a historical investigation, not a setup guide. For current usage, start
with the [README](../../README.md) or [development guide](../../docs/development.md).

Investigated on 5 November 2026, Apple M4, lighter 0.13.8.

**Integration update:** the shared Dockerfile now vendors both the shader I/O
fix and the Metal resource-name fix. The I/O decision is scoped to each shader,
not a process-wide flag. Normal and shader-debug texture checks and the eight
feature cases pass with the vendored build. See the
[production patch notes](../../docker/patches/mesa-25.1.9/README.md).
The sections below preserve the original investigation and measurements.

**The crash is reproducible without the robot. A small textured primitive is
sufficient. A targeted Zink shader I/O patch fixes that reproducer and the full
XLeRobot scene.** The normal simulation and native viewer were left running;
all GPU experiments used separate images and containers.

## What fails

The original image passes the untextured, skybox, multiple-light, fog-settings
and transparency cases. Adding a checker texture makes it abort. The cases with
textured reflective material and combined settings fail too.

This rules out robot meshes, physics, ROS, file transport and scene size as
necessary causes of this particular crash.

The shader dump shows the actual disagreement:

```text
Vertex output:   vec4  slot_4     (texture coordinate xyzw, location 1)
Fragment input:  vec2  slot_4     (texture coordinate xy,   location 1)
Fragment input:  float slot_4_c3  (texture coordinate w,    location 1)
```

Zink represents the fragment input as separate component groups. MoltenVK's
Metal shader interface does not match that representation to the vertex
shader's single vector. The host reports a missing or mismatched `locn1_3`
input when compiling the render pipeline. The subsequent Venus abort obscures
that earlier shader error.

An ordinary linked GLSL program using `xy` and `w` passes on the original
image. The failing texture path is important: not every shader using only part
of a vector triggers the mismatch.

There is a second, diagnostic-only failure: enabling `ZINK_DEBUG=nir` preserves
shader resource names. A generated resource named `sampler` then shadows Metal's
built-in `sampler` type, and shader compilation fails with a different error.
The patched shader dump confirms the texture interface is now vec4 on both
sides, but that debug run still aborts on the reserved-name collision. Normal
runs without shader debug output pass. This separate naming issue is not fixed
by the candidate patch.


## Candidate fix

The experimental image applies only the `zink_compiler.c` part of the
[BAR-on-Apple-Silicon Mesa patch](https://github.com/Meliorative-peasant63/bar-on-apple-silicon/blob/main/patches/mesa-bar-patches.diff).
Its license and attribution are under `patches/`.

For MoltenVK, it merges disjoint fragment input groups and expands eligible
vertex outputs and fragment inputs to matching vec4 values at component zero.
It does not disable textures, shadows or reflections. It does not skip failed
draw calls or advertise a higher OpenGL version.

This is a candidate patch, not a promoted default. The borrowed implementation
uses a process-wide driver quirk flag. Before merging into the shared base,
carry that decision through the individual screen/compiler state so mixed
GPU contexts cannot overwrite each other's setting. Arrays and other shader
stages also need broader coverage before calling this a general Mesa fix.

## Results

| Check | Original image | Candidate image |
|---|---|---|
| Untextured primitive | Pass | Pass |
| Checker texture | Abort | Pass |
| Textured reflective material | Abort | Pass |
| Combined scene settings | Abort | Pass |
| Remaining four feature cases | Pass | Pass |
| Full furnished XLeRobot scene | Abort | 30 RGB-D frames pass |
| Standard robot model checks | Previously aborted during rendering | All pass |
| Mod101 robot model checks | Previously aborted during rendering | All pass |
| Isolated ROS camera pipeline | Not usable on the full scene | Synchronized RGB, depth and calibration pass |

The full scene has 483 geometries and 148 meshes. On the same frozen simulation
state, GPU output compared with CPU OSMesa gives:

- Mean absolute RGB difference: **0.02275** on the 0–255 scale.
- Median absolute depth difference: **0.90 mm**.
- 99th-percentile absolute depth difference: **17.2 mm**, including edges.
- Exact segmentation pixel agreement: **99.48%**.

The central depth also agrees with an independent MuJoCo ray intersection
within the existing 3 cm tolerance. The robot model checks verify the diagnostic
room's known wall depth and robot self-filtering.

Short rendering-only measurements at 640 × 480, with the normal CPU simulation
and native viewer still running:

| Profile | Warm RGB + depth + segmentation rate |
|---|---|
| Patched GPU, shadows/reflections/MSAA enabled | About 6.6 frames/s, 30 total frames |
| Patched GPU, fast profile | About 14.3 frames/s, 60 total frames |
| CPU reference, full quality | About 0.32 frames/s, only 3 total frames |

These are exploratory measurements, not a controlled benchmark. They exclude
ROS publication and the robot's compatibility archive. The isolated live ROS
probe received approximately 5 RGB-D frames/s while another full simulation
was running. It proves the pipeline works; it does not establish a 15 Hz
end-to-end camera rate or an improvement over the current live default.

The live probe used its own container, ROS domain 187 and `/tmp` runtime, with
no published ports and no writes to the running robot's runtime directory.
Only the probe container is stopped after the test.

## Reproduce with the vendored build

Build the shared base, then rebuild the consuming robot image:

```bash
# From multiROS:
docker build --target lighter -t multiros:jazzy-lighter -f docker/Dockerfile .
# From XLeRobotROS:
docker compose -f docker-compose.yml -f docker-compose.lighter.yml build ros-dev
```

Run the feature cases from multiROS:

```bash
python3 investigations/rendering/run_matrix.py \
  --image xlerobot:jazzy-lighter \
  --output investigations/rendering/vendored
```

The pre-fix image was retained locally as
`xlerobot:jazzy-lighter-before-shader-fix`; use that image and a separate output
directory to reproduce the original failures. Each case runs in a disposable
container. The experimental Dockerfile and original patch under this directory
are historical artifacts; they require the pre-vendoring Mesa builder snapshot.
Current builds use `docker/Dockerfile` and `docker/patches/` instead.

`full_scene.py` reads a generated scene and physics snapshot without stepping
physics. It saves the exact state, RGB, depth, segmentation and timing summary.
The local `full-gpu/` and `full-cpu/` directories hold the original captures;
`compare_frames.py` verifies identical state and computes image differences.
`live_probe.py` checks synchronized ROS camera output in an isolated container.

The shared checker now includes a texture. Normal and `ZINK_DEBUG=nir` runs must
both pass before accepting changes to this backend. Live mapping, dashboard
and navigation validation belongs in XLeRobotROS as the integration test.
