# Robot starter

Copy these files into the robot repository and choose a unique project name.
Add and commit the shared dependency:

```bash
git submodule add https://github.com/ringfour/multiROS.git tools/multiros
pixi install
```

Commit `pixi.lock`. Extend the Dockerfile with this robot's packages; keep its
existing source layout. `up` initializes pinned modules, builds the rendering
base and service image, then starts an idle development container.

Configure `commands` before using `sim`, `sim-stop` or `test`. Commands are
arrays, executed on the host or through the container's sourced entrypoint:

```json
"sim": {"where": "container", "argv": ["ros2", "launch", "my_robot", "sim.launch.py"]}
```

Set the top-level `entrypoint` to the robot's sourced wrapper. Configure
`workspace` for colcon builds and `viewer` for a passive native frontend if used.
Add platform GPU overrides only when validated; the starter does not request
hardware devices by default.

Docker uses `compose.yaml`. Windows uses the explicit `container` section via
`wslc`, without Compose. Keep image, paths and required environment consistent.
See [runner configuration](https://github.com/ringfour/multiROS/blob/main/docs/runner.md).

Preview commands before running:

```bash
python tools/multiros/run.py --dry-run up
python tools/multiros/run.py --runtime wslc --dry-run up
```
