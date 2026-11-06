# Getting started

multiROS runs from a robot repository. You use Pixi on the host to start its
containers, run the robot and open a native viewer. The robot's own README is
the place to find its dashboard address, available configurations and extra tasks.

[← README](../README.md)

## Requirements

- [Git](https://git-scm.com/) for the robot and its pinned dependencies.
- [Pixi](https://pixi.sh/) for host tools and the optional viewer environment.
- A container runtime: normally Docker with Compose. See [Platforms](platforms.md)
  for WSL/Docker Desktop, macOS/lighter and the experimental Windows WSLC path.

The normal host environment needs Python, not ROS. A MuJoCo viewer environment
also needs the exact engine version used by that robot's simulator.

## Run an integrated robot

Clone the robot repository with its submodules, or initialize them in an
existing checkout:

```bash
git submodule update --init --recursive
pixi install --locked
pixi run doctor
```

`doctor` reports the selected runtime, backend and source revisions. If the
runtime is reachable, build/start the project and launch its simulation:

```bash
pixi run up
pixi run sim
```

Keep that terminal open. In another terminal in the same robot repository:

```bash
pixi run view
```

The first image build can take a while. Later runs reuse the container image
and the robot's build volumes. `up` starts the environment; `sim` starts the
robot inside it. Some recipes also prepare assets or start a middleware router.

Use `pixi run sim-stop` to stop the robot gracefully. Use `pixi run down` to stop
the project's containers; named volumes are retained. Closing the viewer alone
leaves physics, cameras and ROS running.

See [Commands](commands.md) for rebuilding after changes. The
[XLeRobot integration](../examples/xlerobot/README.md) shows a robot recipe;
[Mr Handy](https://github.com/cristidragomir97/mr_handy) uses the same host workflow
around its C++ `mujoco_ros2_control` simulator.

## Try the viewer on its own

You can inspect the included scene without building a ROS image or starting a
simulation. From a terminal outside this repository:

```bash
git clone https://github.com/ringfour/multiROS.git
cd multiROS
pixi install --locked
pixi run -e mujoco example-view
```

This opens a static model. It does not run physics or connect to a robot.

## Add your own robot

Keep your working simulator and controller setup. The [robot integration guide](porting.md)
walks through adding the shared runner, defining tasks and exporting state for
the native viewer. You can start with container commands and add viewing later.
