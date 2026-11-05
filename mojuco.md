# MuJoCo: container simulation, native 3D frontend

Physics, simulated camera rendering and ROS run inside the Linux container. The host runs
an accelerated interactive 3D viewer. Closing that viewer must not interrupt
camera frames, visual odometry or mapping.

This replaces the first prototype, which rendered RGB-D on the host and sent
images back through shared files. That image round trip is no longer part of
the design.

## Who runs what

The container physics process receives actuator commands from ROS controllers
and calls `mj_step`. It owns contacts, joint dynamics and simulation time.

A separate camera process in the container loads the same model and follows
physics snapshots. It calls `mj_forward` to reconstruct derived state, then
renders color, depth and segmentation. It uses segmentation to mask robot
pixels from a copy of the depth image. Color, raw depth and filtered depth are
published directly as ROS messages, with the simulation timestamp of the state
that produced them. The camera process never steps physics.

The native frontend also loads MuJoCo and the model. It follows pose snapshots,
calls `mj_forward`, and draws the interactive viewport using the host graphics
stack. It neither advances physics nor produces simulated sensor images.

There is one physics owner and separate model/state copies for camera rendering
and the frontend. The host needs MuJoCo and NumPy, but the viewer does not need
a native ROS workspace.

## Current data flow

```text
Docker                                           Host

ROS controllers
      |
MuJoCo physics ---- viewer.npz -----------------> Native 3D frontend
      |
 physics.npz
      |
RGB-D camera renderer
      |
      +--> ROS images --> visual odometry / mapping / dashboard
      |
      +--> state.npz --> diagnostic checks / browser previews
```

The camera renderer publishes from its in-memory arrays. It does not write an
image file and read it back to construct ROS messages. `state.npz` remains a
compatibility output for existing checks and browser previews.

| File | Writer | Readers | Contents |
|---|---|---|---|
| `scene.xml`, `robot.xml`, `staged/` | Container scene setup | Container camera and host frontend | Generated scene and assets |
| `physics.npz` | Container physics | Container camera | Time, positions, velocities and actuator controls |
| `viewer.npz` | Container physics | Host frontend | The same state on a separate update schedule |
| `state.npz` | Container camera | Checks and browser preview process | Rendered RGB-D and corresponding simulation state |

Files live in the bind-mounted `.runtime/` directory. A writer saves a temporary
file, closes it, and atomically replaces the published file. Readers poll for
updates. New snapshots replace old ones; there is no frame backlog.

Physics snapshots use the configured camera rate, normally 15 Hz of simulation
time. Viewer snapshots are scheduled at 50 Hz. Actual rates depend on execution
speed. Scene asset paths are made relative, and meshes outside the repository
are staged so the host can load the generated scene.

## Rendering without a window

Offscreen camera rendering still creates a graphics context. It needs a working
OpenGL implementation even though no desktop window opens in Docker.

On Linux, the intended backend is EGL with the appropriate GPU devices and
drivers. Windows uses the WSLC runtime with GPU access and an initial Mesa D3D12
configuration. Both Linux and Windows need validation on the target hardware.

On macOS, lighter exposes Vulkan through Venus, MoltenVK and Metal. MuJoCo uses
OpenGL, so Zink translates its rendering calls into Vulkan. The test setup in
the earlier GPUAccelerationTest project supplied the Mesa 25.1.9 recipe. The
shared multiROS lighter base builds that recipe against Ubuntu Noble to keep
the libraries compatible with ROS Jazzy. XLeRobotROS extends that base with
its own packages and simulator dependencies. It selects system Venus separately from
the custom Zink build.

A Vulkan device appearing in a probe is not enough. The actual MuJoCo test must
report a hardware renderer and produce correct color, metric depth and
segmentation. Run `pixi run check-rendering` in XLeRobot; use
`--require-accelerated` to reject software rendering.

The original Zink build crashed on textured scenes because its vertex and
fragment shader interfaces did not match after Metal translation. The shared
multiROS image now vendors that shader I/O fix and a separate fix for Metal
resource names used by shader debug output. See the
[patch notes](docker/patches/mesa-25.1.9/README.md) and
[investigation](investigations/rendering/README.md).

XLeRobot's lighter configuration defaults to EGL/Zink GPU sensor rendering.
Its fast profile disables multisampling, shadows and reflections to reduce
latency; resolution, calibration, depth and segmentation remain unchanged.
Set `XLEROBOT_RENDER_QUALITY=standard` for those visual effects.

The explicit `cpu` backend uses OSMesa/llvmpipe. Both paths keep sensors
inside the container.

## What is still expensive

At 640 × 480, RGB occupies about 0.92 MB. Raw and filtered float32 depth occupy
about 1.23 MB each. Together they total about 3.38 MB per frame, or 51 MB/s at
15 Hz before message and archive overhead.

Those frames no longer make a host-renderer round trip. Rendering still costs
GPU time, and publishing ROS images requires readback and copies. The optional
compatibility archive also costs serialization and file traffic. Because it
currently lives on the bind mount, container-local production does not eliminate
all shared-filesystem overhead.

The next transport improvement is to move internal exchanges to container-local
shared memory or storage, and keep only frontend scene/state updates crossing
the host boundary. A persistent socket or Zenoh stream could replace the
frontend snapshot polling. Model files and meshes can stay on disk.

## Starting and stopping

```bash
# From XLeRobotROS:
pixi run up
pixi run sim standard slam:=rtabmap

# Separate terminal; optional:
pixi run view
```

The camera renderer starts with the ROS launch. Start the native frontend
separately; no host camera renderer is needed.

The simulation wrapper holds a lifetime lock to prevent two physics owners.
The camera process exits with the launch; an unexpected camera exit shuts down
the launch rather than leaving a simulation silently running without sensors.
Restart the native frontend when changing scenes or robot configurations: it
does not currently reload its model automatically.

Host RViz is a separate connection problem. It consumes ROS topics and TF,
not MuJoCo snapshot files, and still needs host/container ROS connectivity.

## Implementation files

Paths below are relative to `/Users/cdr/Work/XLeRobotROS`:

- `src/xlerobot_sim/xlerobot_sim/node.py`: physics and state snapshots.
- `src/xlerobot_sim/xlerobot_sim/renderer.py`: RGB-D rendering from snapshots.
- `src/xlerobot_sim/xlerobot_sim/camera.py`: container rendering and ROS publication.
- `tools/multiros/multiros/viewer.py`: shared native interactive frontend.
- Shared `multiROS/docker/Dockerfile`: patched Zink build and rendering base.
- `checks/check_rendering.py` in multiROS: GL renderer and RGB-D check.
- `docs/validation.md` in XLeRobot: recorded robot checks and limits.
