# Windows with wslc

Windows uses Microsoft's built-in WSL container runtime. Pixi and the native
MuJoCo viewer run on Windows; ROS, physics and sensor rendering run in Linux
containers. Docker Desktop is not required.

Microsoft requires WSL 2.9.3 or newer. In PowerShell:

```powershell
wsl --update
wsl --version
wslc version
wslc run --rm hello-world
```

See [Microsoft's overview](https://learn.microsoft.com/en-us/windows/wsl/wsl-container)
and [tutorial](https://learn.microsoft.com/en-us/windows/wsl/tutorials/wsl-containers).

## Adapter

multiROS invokes `wslc build`, `run`, `exec` and container lifecycle commands
directly. It does not invoke Docker or assume Compose support. The first adapter
handles one persistent runtime container, named from the project and service.
Bind mounts carry source and viewer snapshots; named volumes retain build,
install and log data. Published ports bind to loopback.

Windows selects this adapter automatically. Elsewhere, inspect its planned
commands without running them:

```bash
python run.py --config /path/to/robot/multiros.json --runtime wslc --dry-run up
```

CLI flags were checked against Microsoft's
[WSLC source](https://github.com/microsoft/WSL/tree/master/src/windows/wslc/commands).
The adapter has command-planning tests on macOS. It has not been executed on a
Windows machine yet. Verify the installed release's flags using `wslc run --help`
and `wslc build --help` if a command is rejected.

## Graphics

The adapter requests GPU access with `--gpus all`. XLeRobot initially selects
EGL and Mesa D3D12. That path still needs validation on the actual GPU/driver.
CUDA availability is not evidence that offscreen OpenGL works.

Run the textured RGB, known metric depth and segmentation check before loading
the full scene. If acceleration fails, a deliberate `cpu` backend can isolate
runtime/mount problems from GPU problems. Report that run as software rendering.

The native viewer reads the shared scene and snapshots. Check generated mesh
paths, file replacement and image correctness on Windows. Remote state over
sockets remains separate work.

## Resources and persistence

`wslc settings` opens `%LOCALAPPDATA%\wslc\settings.yaml`. CPU, memory and storage
settings there control the WSLC session; `.wslconfig` does not. See
[Microsoft's settings reference](https://learn.microsoft.com/en-us/windows/wsl/wsl-container-settings).

`down` stops this project's simulator before stopping its container. It does
not remove volumes. To apply a new image or mount configuration, stop the
project, remove only its stopped container, then run `up` again.
