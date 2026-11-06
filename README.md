# multiROS

multiROS gives your ROS robot a common workflow for setup, simulation and
development. ROS runs in Linux containers; a native MuJoCo window lets you watch
the simulation from your desktop.

Your robot keeps its models, controllers, launch files and middleware. multiROS
provides the host tools, shared rendering images and passive viewer around them.

## What you can do

- Work on a robot without installing ROS on your laptop.
- Start containers, rebuild ROS packages and inspect logs through Pixi tasks.
- Watch a live simulation in a separate window, while cameras and physics keep running in Docker.
- Reuse the same tools across robots without copying their setup scripts.

## Quick start

Install [Pixi](https://pixi.sh), Git and your platform's
[container runtime](docs/platforms.md). From a robot repository that uses multiROS:

```bash
pixi install --locked
pixi run doctor
pixi run up
pixi run sim
```

In another terminal, open its native viewer:

```bash
pixi run view
```

Closing the viewer leaves the simulation running. Use `pixi run sim-stop` to
stop the simulation, or `pixi run down` to stop the project's containers too.

**New here?** [Getting started](docs/getting-started.md) covers the requirements,
the standalone viewer example and the first run. To bring an existing robot
into this workflow, follow [Adding a robot](docs/porting.md).

## Documentation

| Guide | What you'll find |
| --- | --- |
| [Getting started](docs/getting-started.md) | Installation and your first session |
| [Commands](docs/commands.md) | Daily workflow, rebuilds and shutdown |
| [Configuration](docs/configuration.md) | Robot commands, paths, Compose and viewer settings |
| [Platforms](docs/platforms.md) | WSL, Linux, macOS and the experimental WSLC adapter |
| [Simulation and viewing](docs/simulation.md) | How the viewer follows physics, plus the snapshot format |
| [Troubleshooting](docs/troubleshooting.md) | Runtime, graphics and viewer problems |

XLeRobotROS has been tested on Apple Silicon/macOS with lighter and on WSL2
with Docker Desktop. Mr Handy has also been tested on WSL2. Native Linux GPU
paths and the PowerShell/WSLC runtime still need validation. See the
[validation record](VALIDATION.md) for the tested setups and limits.

## Development

See [Working on multiROS](docs/development.md) for tests and rendering-image
builds, and [Architecture](docs/architecture.md) for the boundaries between
shared tools and robot code. Driver investigations are kept under
[`investigations/`](investigations/rendering/README.md).

## License

[Apache-2.0](LICENSE). Vendored Mesa patches retain their
[attribution and MIT license](docker/patches/mesa-25.1.9/README.md).
