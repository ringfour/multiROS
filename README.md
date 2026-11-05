# multiROS

Shared host tools and rendering images for containerized ROS robots.
Robot descriptions, controllers, middleware and launch files stay with each robot.

Pixi runs the host commands. Linux containers run ROS, physics and simulated
cameras. A native MuJoCo frontend displays state without stepping physics.

| Host | Runtime | Status |
| --- | --- | --- |
| macOS Apple Silicon | Docker/lighter with patched Mesa | Tested with XLeRobotROS |
| Linux | Docker Compose | Runtime testing pending |
| Windows | Microsoft `wslc.exe` | Adapter implemented; Windows testing pending |

## Use it in a robot

Keep a small robot-owned `pixi.toml` and `multiros.json`, and pin this repository
as a submodule at `tools/multiros`. The [starter](templates/robot/README.md) and
[XLeRobot integration](examples/xlerobot/README.md) show the arrangement.

```bash
git submodule add https://github.com/ringfour/multiROS.git tools/multiros
```

The shared runner provides setup, image builds, container lifecycle and native
viewing. Robot commands are argument arrays, not a copied shell dispatcher.
See [runner configuration](docs/runner.md) and [porting a robot](docs/porting.md).

## Work on multiROS

```bash
pixi install --locked
pixi run doctor
pixi run -e mujoco test
pixi run -e mujoco example-view
```

Create a starter with `pixi run core init /path/to/new-robot`. Existing files
are never overwritten. The default environment contains Python only; the
optional MuJoCo environment adds frontend dependencies.

## Rendering images

```bash
docker build --target runtime -t multiros:jazzy-rendering -f docker/Dockerfile .
docker build --target lighter -t multiros:jazzy-lighter -f docker/Dockerfile .
```

Both use ROS Jazzy on Ubuntu Noble. `runtime` provides EGL/Vulkan/OSMesa
libraries. `lighter` adds patched Mesa Zink 25.1.9 for Venus/MoltenVK on macOS.
Robot images add their own simulator versions and packages.

Run `multiros-check-rendering --require-accelerated` inside a robot image with
MuJoCo, NumPy and PyOpenGL. It checks textured RGB, a known metric depth and
segmentation, and reports the actual GL renderer.

The [Mesa patches](docker/patches/mesa-25.1.9/README.md) retain their attribution
and MIT license. [Rendering investigation](investigations/rendering/README.md)
and [validation](VALIDATION.md) record the tested limits.

## Design notes

- [Architecture](specs.md)
- [Repository comparison and ownership](docs/shared-core.md)
- [Windows / wslc](docs/windows-wslc.md)
- [MuJoCo state exchange](mojuco.md)
- [Snapshot format and example](examples/mujoco/README.md)
