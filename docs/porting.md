# Adding a robot

Start with a robot that already builds and runs. multiROS can wrap its workflow
without replacing its simulator, controllers or source layout.

[← README](../README.md) · [Configuration](configuration.md)

## 1. Record the working setup

Identify the physics/control owner, sensor publishers and middleware. Keep the
commands that build and launch it, along with its source paths, ports, assets
and GPU/device requirements. Choose one simulation profile to validate first.

For an assembly, record which component owns each description and driver.
Keep assembly compatibility patches in that assembly's recipe.

## 2. Add the shared tools

From the robot repository:

```bash
git submodule add https://github.com/ringfour/multiROS.git tools/multiros
```

Keep the dependency pinned to a commit. For an empty recipe, generate starter
files from a separate multiROS checkout:

```bash
pixi run core init /path/to/my_robot
```

The starter refuses to overwrite existing files. It supplies an idle container
and task/configuration examples; it does not invent a simulation command.

## 3. Define the robot commands

Adapt `pixi.toml`, Compose and the Dockerfile to your existing
setup. Choose a unique project name. Put source paths and commands in the
[configuration](configuration.md), and source ROS/the workspace in the
container entrypoint.

Keep host task definitions small. A multi-service robot can retain its existing
startup script as a custom host command so routers and asset preparation are
preserved. Reusable runner behavior belongs in multiROS; robot-specific setup
stays in the recipe.

Use the shared rendering image when it fits, or keep the existing image with
`rendering_base: false`. Keep middleware selection and hardware devices at the
robot/profile level.

## 4. Check setup before launching

Install and commit the host lockfile, inspect the runtime and preview commands:

```bash
pixi install
pixi run doctor
python tools/multiros/run.py --config pixi.toml --dry-run up
```

Use `pixi install --locked` for subsequent validation. Add only platform GPU
backends that the recipe can configure, and test their actual renderer. Source
pins, asset checksums and image versions belong with the robot release.

## 5. Add graceful shutdown

Implement `sim-stop` for this project's simulator and connect it to the runner.
It should request normal shutdown and wait for the robot to release its session
lock/save state. Avoid host-wide process matching that could stop another robot.

Test closing/reopening a viewer, stopping/restarting the simulation and stopping
the project with another robot present. Preserve named volumes during normal
shutdown.

## 6. Connect the native viewer

Export complete display state from the existing physics owner. Include the
free base and loose objects; joint feedback alone is insufficient. Use a model
that the host can load and the [schema-1 snapshot format](simulation.md#snapshot-format).
MJB can embed assets that otherwise exist only inside the image.

Give the viewer a separate Pixi environment with the exact engine version.
Keep camera rendering in the container. A passive window should neither step
physics nor own ROS control. Gazebo uses its own transport instead of this
MuJoCo adapter.

## 7. Validate the profile

Build from a clean checkout without unrelated sibling installations. Check
textured RGB/metric depth, clock, TF, controllers, command timeout behavior and
a small appropriate motion. Measure simulation speed, sensor rate/age and
window FPS separately.

Record the actual host/runtime/GPU/engine and any limits. Validate new component
versions and real hardware separately. Keep the old recipe available until the
replacement workflow has passed those checks.
