# Working on multiROS

Use this repository to change shared host tools, the passive viewer and rendering
images. Robot models, launch files and runtime packages stay in robot repositories.

[← README](../README.md) · [Architecture](architecture.md)

## Install and check

```bash
git clone https://github.com/ringfour/multiROS.git
cd multiROS
pixi install --locked
pixi run doctor
pixi run -e mujoco test
```

The optional `mujoco` environment includes viewer dependencies and runs the
snapshot/model tests. Without them those tests are skipped. The core example
pins MuJoCo 3.13.0; a robot viewer environment must match that robot's engine.

To inspect the included static model:

```bash
pixi run -e mujoco example-view
```

This opens a window but does not start simulation. For CLI changes, validate a
robot command plan with `--dry-run` before exercising its runtime. Documentation
changes need link/example checks; they do not require starting a robot.

## Test a robot integration

Use its explicit shared-source override when available, such as
`MULTIROS_ROOT=/path/to/multiROS pixi run doctor` in XLeRobot or Mr Handy.
Confirm the selected checkout in `doctor` before testing.

Run checks appropriate to the change: command planning for runner changes,
model/snapshot checks for viewing, and actual RGB-D/control checks for runtime
changes. Record the host, engine, graphics backend and limitations in
[VALIDATION.md](../VALIDATION.md) or the robot's validation guide.

Commit and publish shared changes before updating a robot's submodule pin to
that commit. Keep Pixi lockfiles with their manifests. Host locks do not freeze
apt packages or mutable container image tags.

## Rendering images

multiROS owns two Linux rendering bases: `runtime` for EGL/OSMesa and `lighter`
for patched Mesa on Apple Silicon. WSL, DRI and CPU select different host/device
profiles against the runtime base rather than duplicating ROS images per OS.
The shared [graphics profiles](../docker/compose/README.md) own driver variables
and device mounts. Robot repositories extend a base with their own packages.
These images are currently built locally; no published image registry is configured.

Build the bases with:

```bash
docker build --target runtime -t multiros:jazzy-rendering -f docker/Dockerfile .
docker build --target lighter -t multiros:jazzy-lighter -f docker/Dockerfile .
```

`runtime` supplies EGL/Vulkan/OSMesa libraries. `lighter` adds patched Mesa Zink
25.1.9 for the tested Venus/MoltenVK path on Apple Silicon. Robot images add
their own simulator versions and ROS packages. An existing robot image can be
retained by setting `rendering_base: false`.

Validate graphics in the resulting robot image using its actual MuJoCo version:

```bash
multiros-check-rendering --require-accelerated
```

This diagnostic needs MuJoCo, NumPy and PyOpenGL in that image. It checks a small
textured scene, reference metric depth and segmentation; full robot scenes need
robot-specific checks as well.

## Investigations

Keep experiments and raw measurements under `investigations/`, with the tested
versions and conditions. Promote a result to the user guides only once its
workflow and limits are understood.

The [Mesa investigation](../investigations/rendering/README.md) preserves the
original texture failure and experiments. Production patches have separate
[attribution and license notes](../docker/patches/mesa-25.1.9/README.md).

The [camera pipeline audit](../investigations/rendering/camera-pipeline-audit.md)
compares our integrations with MuJoCo and Gazebo reference code.
