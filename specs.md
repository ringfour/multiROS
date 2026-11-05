# multiROS architecture

The goal is one development workflow across macOS, Linux and Windows, without
installing ROS on every developer machine.

## Ownership

Pixi manages host tools and tasks. A Linux container owns ROS, simulator physics,
controllers and offscreen sensor rendering. Native frontends display received
state. Closing a frontend must not stop physics or cameras.

Docker Compose is the current macOS/Linux runtime. Windows uses Microsoft's
`wslc.exe` through a separate adapter. Docker Desktop is not required there.
GPU configuration is platform-specific and must pass a real rendering test.

Robot repositories own models, controllers, launch arguments, middleware,
assets, hardware drivers and optional services. multiROS owns lifecycle tools,
rendering bases, diagnostics and reusable frontends. It does not select a
universal physics engine or install navigation in every robot image.

## Dependencies

Each robot pins multiROS as a Git submodule. A small template supplies files
the robot will own. Shared fixes arrive by updating the submodule commit,
without copying another management script.

Commit Pixi lockfiles and component source pins. Record asset checksums and
retain release images by digest. A Git revision does not pin mutable apt
repositories or image tags. Developer source overrides must be explicit.

## Simulation

Preserve the existing physics and control owner: XLeRobot's Python simulator,
`mujoco_ros2_control`, Unitree's simulator, or Gazebo. Export display state from
that owner. Native MuJoCo viewing only performs forward kinematics.

Render RGB/depth inside the runtime and publish it directly to ROS. Never send
state to the host to generate camera frames and return those pixels to ROS.
The interactive host frontend renders its own display independently.

XLeRobot currently exports atomic local snapshots. The shared reader supports
a versioned display envelope and an explicit legacy adapter. Remote runtimes
will need a socket transport. Sensor rendering and restartable checkpoints
need more state than this display protocol promises.

Gazebo keeps its native server/client transport. Its rendering-based sensors
remain on the server. Gazebo cameras and native RViz packaging are unvalidated
in this environment; neither is required by every robot.

## Current implementation

The runner handles pinned submodule setup, rendering/robot image builds,
workspace builds, sourced container commands, graceful simulation shutdown,
container lifecycle and passive native viewing. Robot commands and paths live
in `multiros.json`. The same task names work through Docker or the WSLC adapter.

XLeRobot is the integration test. The next backend is mod101 bench simulation,
followed by base101, Handy composition and G1. Preserve their existing control
ownership and middleware constraints; see [the comparison](docs/shared-core.md).

## Support criteria

A migrated profile must build from a clean checkout, without ambient sibling
builds. Check its real renderer, RGB/depth, clock, TF, controllers and a small
robot-appropriate motion. Verify that closing the viewer leaves sensors running,
and stopping one project leaves other projects alone.

Dependency resolution for an OS is not runtime validation. Record the host,
architecture, runtime, GPU driver and engine versions for each tested profile.
Hardware deployment is separate: a Windows developer may use a Linux robot,
and host portability does not imply universal USB passthrough.
