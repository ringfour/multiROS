# Commands

The usual session is `up`, then `sim`, with `view` in another terminal. Run
these tasks from the robot repository, not from the multiROS checkout.

[← README](../README.md)

## Daily workflow

```bash
pixi run up                  # Prepare and start the runtime
pixi run sim                 # Start the robot; keep this terminal open
```

In another terminal:

```bash
pixi run view                # Open the passive native viewer
pixi run status              # Check this project's containers
```

When finished:

```bash
pixi run sim-stop            # Stop the simulation gracefully
pixi run down                # Stop containers; keep volumes
```

Pixi tasks belong to the robot. The table below describes the shared runner's
actions; a recipe may expose fewer tasks or wrap setup for its own assets and
services. Check that robot's README for differences.

## Command reference

| Task | What it does | When to use it |
| --- | --- | --- |
| `setup` | Initialize configured Git submodules at their recorded commits | After cloning or changing source pins |
| `doctor` | Report host/runtime versions, backend and Git provenance | Before the first run or when setup fails |
| `images` | Initialize sources and build configured images | After changing image dependencies |
| `up` | Build/start the runtime; stop an active sim before Docker replacement | Start a development session |
| `build` | Run the configured colcon workspace build | After changing ROS source |
| `sim` | Run the robot's configured simulation command | Start physics, sensors and control |
| `sim-stop` | Run the robot's graceful shutdown command | Stop the robot while keeping containers |
| `view` | Open the shared native MuJoCo frontend | Watch a simulation or inspect a model |
| `exec` | Open a sourced container shell, or run a command | Inspect the ROS environment |
| `status` | Inspect this project's runtime | Check whether containers are running |
| `logs` | Follow runtime logs | Diagnose startup or background processes |
| `test` | Run the robot's configured check command | Validate that robot profile |
| `restart` | Stop the sim, then restart the runtime | Restart the environment without an image build |
| `down` | Stop the sim, then stop project containers | Finish a session |

For the shared `down`, `restart` and Docker `up` paths, the shutdown hook runs
when `sim-stop` is configured and the container is running. If shutdown fails,
replacement/stop is aborted so the robot can finish saving state. Robot-owned
startup wrappers are responsible for equivalent handling of their extra services.

## Rebuild after a change

For ROS source changes:

```bash
pixi run build
pixi run sim
```

Stop the existing simulation before launching another. Rebuild selected packages
by appending their names, for example `pixi run build my_robot_control`.

For Dockerfile or container dependency changes, use `images` and `up` if the
recipe exposes those tasks. A robot-owned `up` may handle both itself. Changing
a WSLC image or mount configuration requires recreating its stopped container;
see [Platforms](platforms.md#windows-powershell-and-wslc).

## Inspect commands before running them

Call the runner directly when you need global options. They precede the action:

```bash
python tools/multiros/run.py --config pixi.toml --dry-run up
python tools/multiros/run.py --config pixi.toml --backend dri --dry-run sim
```

Choose only backends declared by the recipe. `MULTIROS_RUNTIME` and
`MULTIROS_BACKEND` can also be set in the process environment before invoking Pixi.
Custom command arguments are appended literally, without host-shell expansion.

## Viewer options

Recipes commonly expose `view` through a separate Pixi environment:

```bash
pixi run view --quality standard
pixi run view --distance 4
```

The default `fast` quality disables shadows and planar reflections.
For `--frontend glfw`, `--rate` caps drawing; for the passive frontend it only
controls state updates. Recipes may select defaults per backend.
See [Simulation and viewing](simulation.md) for model formats and other options.
