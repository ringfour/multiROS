# Configuration

Each robot describes its workflow in `pixi.toml` and exposes it through
Pixi tasks. Store robot settings under `[tool.multiros]`; the runner discovers
that table automatically. Legacy `multiros.json` remains supported for robots
which have not migrated. Compose files and the Dockerfile stay with the robot as well.

[← README](../README.md) · [Adding a robot](porting.md)

## A small Docker recipe

This example wraps one existing ROS service. Replace its paths, package and
launch arguments with those used by your robot:

```toml
[tool.multiros]
schema = 1
project = "my-robot"
compose = ["compose.yaml"]
service = "ros-dev"
submodules = ["tools/multiros"]
entrypoint = ["/usr/local/bin/robot-entrypoint"]
rendering_base = false

[tool.multiros.commands]

[tool.multiros.commands.sim]
where = "container"
argv = ["ros2", "launch", "my_robot", "sim.launch.py", "headless:=true"]

[tool.multiros.commands.sim-stop]
where = "container"
argv = ["python3", "scripts/stop_sim.py"]
```

Use a unique project name so runtime commands address this robot. The entrypoint
should source ROS and the robot workspace before executing its arguments.

## Project and runtime

| Field | Purpose |
| --- | --- |
| `schema` | Configuration version; currently `1` |
| `project` | Lowercase Compose project/container prefix |
| `root` | Optional robot root, relative to the configuration file; defaults to `.` |
| `compose` | Compose files loaded in order |
| `service` | Main development service; defaults to `ros-dev` |
| `backends` | Named lists of additional Compose files, such as `dri`, `wsl` or `cpu` |
| `submodules` | Source paths initialized at their recorded Git commits |
| `entrypoint` | Wrapper prepended to container commands |
| `rendering_base` | Build the shared rendering image before the robot image |

`rendering_base: false` lets a robot keep an existing image, as Mr Handy does
for its C++ simulator. See [image builds](development.md#rendering-images) before
enabling the shared base.

The runner's automatic backend only recognizes Docker's `lighter` context;
otherwise it selects `default`. A robot bootstrap can select a backend after
checking devices, or you can pass `--backend` / `MULTIROS_BACKEND` explicitly.
See [Platforms](platforms.md) for the distinction between WSL and WSLC.

## Robot commands

Each `commands` entry has a location and an argument array:

```toml
[tool.multiros]

[tool.multiros.teleop]
where = "container"
argv = ["ros2", "run", "teleop_twist_keyboard", "teleop_twist_keyboard"]
interactive = true

[tool.multiros.start]
where = "host"
argv = ["bash", "scripts/manage.sh", "start"]
```

`where` is `host` or `container`. Additional CLI arguments are appended to
`argv` literally. A host shell does not expand pipes, variables or wildcards;
include an explicit script when shell behavior is required. `interactive: true`
enables terminal input when the calling process has a terminal.

| Placeholder | Replaced with |
| --- | --- |
| `{root}` | Absolute robot checkout path |
| `{multiros}` | Shared-core checkout path |
| `{python}` | Current host Python executable |
| `{configuration}` | Selected robot variant |

Optional `configurations`, `default_configuration` and `configuration_env`
fields let a recipe accept variants such as `standard` and `mod101`. A matching
first argument selects that variant; remaining arguments go to the command.

For a multi-service setup, a Pixi task can call a custom host action such as
`start`. That script can prepare assets and start a router alongside ROS. The
shared `up` path targets the configured main service; it does not infer a
robot's extra startup steps.

## Workspace builds

Add `workspace` to make `build` invoke colcon in the container:

```toml
[tool.multiros]

[tool.multiros.workspace]
paths = ["src", "dependencies/my_driver"]
packages = ["my_robot_description", "my_robot_control"]
workers = 2
cmake_args = ["-DPython3_EXECUTABLE=/usr/bin/python3"]
```

Paths here are container paths, relative to its working directory when not
absolute. Package names supplied after `build` replace the configured list.
Without `workspace`, the shared `build` action builds the robot image instead.

## Native viewer

`viewer.runtime` names the shared state directory; `viewer.args` adds options
to the passive viewer. This example uses an embedded model:

```toml
[tool.multiros]

[tool.multiros.viewer]
runtime = ".runtime"
args = ["--model", ".runtime/scene.mjb", "--track-body", "base_link", "--kinematics-only"]
```

These arguments are passed as written, relative to the robot's working
directory. Give the viewer its own Pixi environment with the exact simulator
version. See [Simulation and viewing](simulation.md) for XML/MJB models,
quality presets and the state contract.

## Environment values

The runner reads an optional `.env` as `NAME=value` data. It does not execute it
as a shell script, and existing process values take precedence. Runtime/backend
selection happens before that file is loaded, so set `MULTIROS_RUNTIME` and
`MULTIROS_BACKEND` in the calling process or use the global flags.

Robot bootstraps may offer additional overrides. XLeRobot and Mr Handy support
`MULTIROS_ROOT` for deliberately testing another shared-core checkout. `doctor`
reports the path and Git revision being used.

## WSLC container settings

The experimental WSLC adapter uses a `container` section instead of Compose.
It includes `image`, `dockerfile`, `workdir`, `gpu`, `mounts`, `environment`,
`backend_environment` and `ports`. The [starter](../templates/robot/pixi.toml)
shows the layout. Image values can be a string or a map with `default` and
backend names; environment/port strings support `${NAME:-default}` substitution.

The adapter currently manages one persistent container. A multi-service recipe
needs deliberate WSLC integration; its Compose services do not carry over
automatically. See [Platforms](platforms.md#windows-powershell-and-wslc).

## Shared platform profiles

Backend paths may use `{multiros}` to reference the selected shared checkout.
Use the [shared graphics profiles](../docker/compose/README.md) for generic GPU
settings. Keep robot image selection and ROS configuration in the robot recipe.

Viewer `backend_args` can tune one platform without changing the others. User
arguments are appended last so they can override these defaults:

```toml
[tool.multiros.viewer.backend_args]
wsl = ["--frontend", "glfw", "--rate", "15", "--kinematics-only"]
```
