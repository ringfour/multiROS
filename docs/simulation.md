# Simulation and viewing

The simulation owns motion and sensors. The native viewer follows its state
and renders an interactive window. Closing that window leaves ROS, physics and
camera publication running.

[← README](../README.md)

## How it fits together

```text
Linux container                                  Host

Existing physics and controllers
    ├── Camera rendering → ROS → mapping/dashboard
    └── Complete state → viewer.npz ─────────────→ Native MuJoCo window
```

The viewer has no ROS dependency. It never calls `mj_step` or sends actuator
commands back to the robot. Camera images follow the separate ROS/dashboard
path and are not part of the 3D state snapshot. Display state contains the free base and loose objects as well as joints;
`/joint_states` alone cannot represent the whole scene.

XLeRobot uses a Python simulation owner and an explicit legacy snapshot adapter.
Mr Handy exports state from its existing C++ `mujoco_ros2_control` owner and
uses the versioned snapshot format below. Neither integration starts a second
physics owner for viewing.

## Open the window

From an integrated robot, run `pixi run view` while its simulation is active.
For the standalone static example, run this from multiROS:

```bash
pixi run -e mujoco example-view
```

The robot's viewer environment must match its simulator's exact MuJoCo version.
XLeRobot currently uses 3.13.0; the validated Mr Handy integration uses 3.12.0.
The shared runner selects `mjpython` on macOS and Python on Linux/Windows.

## Models and assets

By default the viewer reads `scene.xml` and `viewer.npz` from its runtime
directory. XML assets must resolve on the host: use shared relative paths or
have the robot stage assets into that directory.

An embedded `scene.mjb` is another option. It contains the compiled model and
its assets, so image-only mesh paths need not exist on the host. Select it with
`--model .runtime/scene.mjb`. Match the engine version and validate binary-model
compatibility on each host. Mr Handy uses this path; XLeRobot now selects it
for its WSL frontend as well. Its robot-owned preparation worker compiles once
and exits, so long-lived processes avoid XML compilation caches. XML is retained
for inspection; explicitly selecting it restores that compilation cost. Model
hashing reads incrementally to avoid a whole-MJB temporary allocation.

Restart the viewer when switching simulation sessions, models or robot variants.
It does not reload a changed model automatically.

## Quality and display options

| Option | Purpose |
| --- | --- |
| `--quality fast` | Disable shadows and planar reflections; the default |
| `--quality standard` | Keep full viewer effects |
| `--track-body NAME` | Follow a named model body |
| `--distance`, `--azimuth`, `--elevation` | Set the initial view |
| `--show-group N`, `--hide-group N` | Select geometry groups |
| `--kinematics-only` | Update body/camera/light transforms without sensors, contacts or constraint calculations |
| `--frontend glfw` | Lightweight read-only 3D window with an actual draw cap |
| `--frontend passive` | Full MuJoCo UI; shared-core default |
| `--rate N` | GLFW draw cap (default 15); passive state-sync rate only (default 60) |
| `--width`, `--height` | GLFW window size, default 1280×720 |
| `--pose-tolerance` | GLFW visible-pose redraw tolerance, default 1e-5 |
| `--full-forward` | Override a recipe's kinematics-only setting for full diagnostics |
| `--profile FILE` | Write timing counters on exit |
| `--static` | Inspect a model without requiring snapshots |

`--kinematics-only` is useful for a pose display, particularly when the model
contains expensive sensors such as lidar. Sensor/force/contact visualizations
need additional derived data. Robot cameras have their own quality settings;
changing viewer quality does not change the container camera renderer.

## Lightweight window

XLeRobot selects the GLFW frontend on its WSL backend. Other recipes/platforms
retain their existing defaults. Left drag orbits, right drag pans, the middle
button or scroll wheel zooms, and Escape closes the window. It does not include
the full simulator's sidebars or editing controls.

This frontend shares the loaded model/data directly with its single render loop.
It avoids the passive UI's recurring full-model sync and computes only the body,
camera and light transforms when the recipe selects `--kinematics-only`.
The frame budget includes snapshot/transform/render work rather than sleeping
for a full extra frame afterward. Minimized windows skip drawing; unchanged
rigid visual poses skip redraws. Hidden geom motion alone does not invalidate
the image. Visible poses, tracked/fixed cameras, light motion, input, resize and
exposure trigger redraws. Deformable models conservatively redraw each tick.
The strict tolerance is in metres and rotation-matrix components and only affects
display; it does not modify simulation or sensors.

The passive frontend has its own render thread. Reducing its state-sync rate
does not cap GPU drawing. Keep it when you need its full UI; a recipe can allow:

```bash
pixi run view --frontend passive --full-forward
```

Compressed camera streams serve image previews, not this independent 3D camera.
A stream viewer can reuse captured camera pixels; an orbitable 3D view still
needs rendering from its own viewpoint. See the [viewer audit](../investigations/rendering/viewer-pipeline-audit.md).

## Snapshot format

Schema 1 is a display snapshot, not a physics checkpoint. Publish an NPZ archive
with these fields and no object/pickle arrays:

| Field | Meaning |
| --- | --- |
| `schema` | Scalar integer `1` |
| `session` | Nonempty string identifying the simulator run |
| `sequence` | Nonnegative integer that increases within the session |
| `model_sha256` | SHA-256 of the exact XML or MJB bytes loaded by the viewer |
| `mujoco_version` | Exact engine version string |
| `time` | Finite scalar simulation time |
| `qpos`, `qvel`, `ctrl` | Finite arrays with the model's dimensions |

Write a temporary file in the same directory, close it, then atomically replace
`viewer.npz`. New state replaces old state rather than accumulating a frame
queue. The producer must read physics state safely; copy it under the simulator's
synchronization boundary before publishing from another thread/process.

The reader validates all arrays before changing display state. It rejects a
wrong model/version, an old or repeated sequence, and a changed session. The
first file establishes session identity; the adapter must also establish that
the producer is alive. A leftover snapshot can otherwise look valid on first
attachment.

An XML hash does not cover external meshes/textures, so pin those assets
separately. A compiled MJB includes its embedded asset bytes. Additional state
such as mocap, plugin state or sensor histories may be required by other uses;
this format promises display positions and controls, not restartable physics.

`--legacy-snapshots` accepts time/qpos/qvel/ctrl without the schema metadata for
incremental migrations. It checks shapes and finite values but cannot establish
model, version or session identity. Use schema 1 for new integrations.

## Transport and performance

The current frontend reads local atomic snapshots. Remote state needs a network
adapter; it is not supplied by the file reader. Gazebo keeps its own server/client
transport rather than using this MuJoCo format.

Measure rendering, state transfer and physics separately. The state-sync rate,
rendered window FPS and sensor publication rate are different quantities. Large
meshes, lighting effects, repeated sensor computation and other GPU applications
can each affect them. See [Troubleshooting](troubleshooting.md#rendering-is-slow).
