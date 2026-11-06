# Robot starter

These are starting files for a robot-owned recipe. Give the project a unique
name and adapt the Dockerfile, Compose settings and `pixi.toml` to the
working robot. The initial container is idle; configure `sim`, `sim-stop` and
checks before using them.

Follow [Adding a robot](https://github.com/ringfour/multiROS/blob/main/docs/porting.md) for the integration sequence and
[Configuration](https://github.com/ringfour/multiROS/blob/main/docs/configuration.md) for the fields. Add the shared core
at `tools/multiros` and commit its pin together with the robot's Pixi lockfile.

The starter uses Docker Compose by default and includes a separate WSLC
container specification. Platform GPU devices are deliberately left to the
recipe. See [Platforms](https://github.com/ringfour/multiROS/blob/main/docs/platforms.md) before adding an override.

Preview the recipe from its root:

```bash
python tools/multiros/run.py --config pixi.toml --dry-run up
```

A native viewer is optional. Add its Pixi task/environment and an exporter from
the existing simulation owner as described in
[Simulation and viewing](https://github.com/ringfour/multiROS/blob/main/docs/simulation.md).
