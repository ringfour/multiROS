# Shared graphics profiles

These Compose overrides own platform devices, driver libraries and GL settings.
They target the runner's default service, `ros-dev`. Recipes using another
service need an explicit adapter. They supplement the robot's base Compose file;
they do not define a robot image, ROS packages, launch commands or ports.

Select them in `[tool.multiros.backends]` in the robot's `pixi.toml`:

```toml
[tool.multiros.backends]
cpu = ["{multiros}/docker/compose/cpu.yml"]
dri = ["{multiros}/docker/compose/dri.yml"]
wsl = ["{multiros}/docker/compose/wsl.yml"]
lighter = ["{multiros}/docker/compose/lighter.yml", "docker/compose.lighter.yml"]
```

`{multiros}` resolves to the selected shared checkout, including `MULTIROS_ROOT`
when the robot bootstrap supports that development override. The optional robot
lighter overlay selects its own image and `multiros:jazzy-lighter` build base.
Shared GL overrides use `MULTIROS_MUJOCO_GL` and `MULTIROS_GALLIUM_DRIVER`.
CPU explicitly uses OSMesa/llvmpipe; WSL defaults to EGL/D3D12; lighter defaults
to EGL/Zink. The DRI profile only exposes device nodes, so driver selection still
needs validation on the target machine. See the [platform guide](../../docs/platforms.md).
