# Platforms

The host runs Pixi and, optionally, a native viewer. ROS and simulated sensors
stay in a Linux container. Container graphics depend on the host's GPU path.

[← README](../README.md)

## Tested setups

| Host | Runtime | Status |
| --- | --- | --- |
| WSL2 / WSLg | Docker Desktop | XLeRobot and Mr Handy tested |
| macOS / Apple Silicon | Docker with lighter and patched Mesa | XLeRobot tested |
| Native Linux | Docker Compose | Device overrides exist; GPU integration testing pending |
| Windows / PowerShell | WSLC | Adapter and command-planning tests exist; runtime testing pending |

The optional Windows-native viewer was also exercised against XLeRobot's WSL
state. That does not validate the WSLC container adapter. The detailed
[validation record](../VALIDATION.md) names the engines and limits.

## WSL2 with Docker Desktop

Run the robot commands in the WSL Linux shell. Enable Docker Desktop's WSL
integration for that distribution, then check the connection:

```bash
docker version
docker compose version
pixi run doctor
```

Keep the checkout in the WSL Linux filesystem, such as `~/robots`, as in the
tested setup. WSLg provides the host viewer's window. The tested Intel graphics
path used `/dev/dxg`, WSL's D3D12 libraries and Mesa's `d3d12` driver.

Generic GPU mounts and driver variables live in the shared
[graphics profiles](../docker/compose/README.md). XLeRobot selects the `wsl`
profile from its bootstrap; Mr Handy retains its existing local override until
its integration is updated. The runner only applies the declared profile.

The host viewer and container cameras create separate graphics contexts. Check
both. A working window or CUDA device alone does not establish that offscreen
RGB-D rendering is accelerated.

## Linux with Docker

Use Docker with Compose. A robot can declare a `dri` backend that passes DRM
render nodes into the container:

```bash
MULTIROS_BACKEND=dri pixi run doctor
```

Select only a backend that exists in that recipe. NVIDIA requires its own
container-toolkit/device configuration; a `/dev/dri` override is not an NVIDIA
setup. These native Linux GPU paths still need validation here.

## macOS with lighter

The tested Apple Silicon setup uses lighter to expose a Vulkan GPU through
Venus/MoltenVK. The shared `lighter` image supplies patched Mesa Zink so MuJoCo's
OpenGL rendering can use that path.

The runner recognizes a Docker context named `lighter`; the robot must also
select the shared `lighter` graphics profile and its own image override. See [rendering images](development.md#rendering-images)
and the [Mesa patch notes](../docker/patches/mesa-25.1.9/README.md).

The native MuJoCo frontend runs through `mjpython` on macOS. The shared runner
selects it from the viewer environment.

## Windows PowerShell and WSLC

This is a separate, experimental path: Pixi/viewing run on Windows and WSLC
runs the Linux container, without Docker Desktop. WSL-shell commands use Docker
by default; native Windows selects WSLC.

Start by checking the installed runtime in PowerShell:

```powershell
wsl --version
wslc version
wslc run --rm hello-world
```

Follow Microsoft's [WSL containers overview](https://learn.microsoft.com/en-us/windows/wsl/wsl-container)
for installation requirements and its [tutorial](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers)
for the initial runtime setup. Verify flags against the installed `wslc --help`
if a command is rejected. multiROS has not completed a live WSLC/GPU run.

WSLC uses the explicit `container` settings in `pixi.toml`. The adapter
requests `--gpus all` unless GPU access is disabled or the `cpu` backend is
selected. It supports one persistent container, bind mounts, named volumes and
loopback-published ports. Compose is not invoked on this path.

After an image/mount configuration change, stop the project, remove its stopped
WSLC container, then run `up` again. Named volumes remain. `wslc settings`
controls the WSLC session's resources; see Microsoft's
[settings reference](https://learn.microsoft.com/en-us/windows/wsl/wsl-container-settings).

To inspect the planned commands without running them:

```bash
python run.py --config /path/to/robot/pixi.toml --runtime wslc --dry-run up
```

## Check the actual renderer

The shared image includes `multiros-check-rendering`. Run it inside a robot
image with MuJoCo, NumPy and PyOpenGL installed. It reports OpenGL's renderer
and checks textured RGB, a known metric depth and segmentation. A recipe may
expose it as `pixi run check-rendering`; others supply a robot-specific check.

If the renderer is software-based or frames are slow, continue with
[Troubleshooting](troubleshooting.md#rendering-is-slow).
