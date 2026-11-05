# Runner configuration

The runner reads robot-owned `multiros.json`. Pixi tasks invoke it through the
pinned `tools/multiros` checkout. It needs Python 3.12; ROS stays in the container.

```bash
python tools/multiros/run.py doctor
python tools/multiros/run.py --dry-run up
python tools/multiros/run.py --runtime wslc --dry-run sim
```

Global options precede the action. `--runtime auto` chooses WSLC on Windows and
Docker elsewhere. `--backend auto` recognizes Docker's `lighter` context;
otherwise it uses `default`. Select Linux device overrides explicitly.
`MULTIROS_RUNTIME` and `MULTIROS_BACKEND` set the same options.

## Configuration fields

| Field | Purpose |
| --- | --- |
| `schema` | `1` |
| `project`, `service` | Project/container identity; choose a unique project |
| `compose`, `backends` | Docker Compose files and optional GPU overrides |
| `submodules` | Source paths initialized at their recorded commits |
| `rendering_base` | Build the shared runtime/lighter image before the robot image |
| `entrypoint` | Sourced wrapper used for container commands |
| `container` | WSLC image, workdir, mounts, environment and ports |
| `workspace` | Colcon source paths, packages, worker limit and CMake arguments |
| `commands` | Robot-specific host/container argument arrays |
| `viewer` | Shared runtime directory and native MuJoCo viewer arguments |
| `configurations` | Optional robot variant names, e.g. standard/mod101 |

`commands` entries have `where: host|container` and `argv: [...]`. Additional
CLI arguments are appended literally. `{root}`, `{multiros}` and `{python}`
substitute host paths; `{configuration}` selects the robot variant. Container
commands should use Linux paths. No host shell interprets these arrays.
Set `interactive: true` for terminal input, such as keyboard teleoperation.

The optional `.env` is parsed as `NAME=value` data, not sourced as a shell
script. Explicit process environment values take precedence. WSLC environment
and port values support `${NAME:-default}` substitution.

## Actions

- `setup` initializes configured Git submodules recursively, without updating branches.
- `images` runs setup and builds the shared rendering and robot images.
- `up` builds and starts the service, stopping an active simulation gracefully
  before replacing a Docker container. An existing WSLC container is started in place.
- `build` rebuilds the configured ROS workspace; package names can follow it.
- `sim`, `sim-stop`, `test` and other robot commands use the configured entrypoint.
- `view` launches the shared passive viewer, using `mjpython` on macOS.
- `down` and `restart` first run `sim-stop` if the project's container is running.
  If shutdown fails, the container is left alone so map saving can finish.
- `exec`, `status` and `logs` address this project only.

`down` preserves containers and volumes. For WSLC image/config changes, stop the
project, remove its stopped container by name, then run `up`; named volumes
remain. WSLC supports one runtime container in this adapter. Multi-service
robots still use their existing Compose topology until ported deliberately.

`doctor` reports host/runtime versions and Git provenance. It does not certify
GPU rendering. Run the rendering diagnostic inside the robot image.

The default Pixi environment only contains host Python. Native viewer dependencies
belong in an optional environment with a simulator version matching that robot.
Source checkout/submodule use is the supported packaging path; template and
Docker assets are not shipped as a standalone wheel.
