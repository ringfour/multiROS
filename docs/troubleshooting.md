# Troubleshooting

Start with the robot's `pixi run doctor` and the output in its `sim` terminal.
The checks below help separate runtime setup, physics, graphics and viewing.

[← README](../README.md)

## Docker is not reachable

```bash
docker version
docker compose version
pixi run doctor
```

On WSL, run these in the intended distribution and enable its Docker Desktop
integration. On macOS, check the active Docker context. If the selected backend
is not listed in the robot's `pixi.toml`, choose one that is configured.

Native Windows selects WSLC, not Docker. Use the
[platform guide](platforms.md#windows-powershell-and-wslc) to inspect that path.

## Setup or a build fails

Initialize submodules and install the committed host environment:

```bash
git submodule update --init --recursive
pixi install --locked
```

A lockfile mismatch needs a deliberate dependency update, not an unlocked
install during validation. A ROS source change needs a workspace build; a new
system package needs an image build. See [Commands](commands.md#rebuild-after-a-change).

The default host environment may not contain MuJoCo. Use the recipe's `view`
task so the optional viewer environment is selected. Run ROS tools through
`pixi run exec`, where the robot's entrypoint sources the container workspace.

## The viewer cannot find its model or state

Start the simulator first and check its configured runtime directory. The
producer must publish the model, host-resolvable assets and `viewer.npz`.
An XML file referring to `/opt/...` inside an image is not enough for a host
viewer. Stage the assets or use an embedded MJB model.

A schema-1 version/model error means the viewer and producer do not match.
Use the exact engine version, regenerate the model/state, and restart the
viewer. A changed session also requires restarting the viewer. Do not bypass
these checks with the legacy option for a new exporter.

See [the snapshot contract](simulation.md#snapshot-format).

## Rendering is slow

Measure these independently:

1. **Simulation speed:** compare elapsed simulation time with wall time.
2. **Sensor rate and age:** inspect source timestamps as well as message counts.
3. **Window FPS:** measure actual rendered frames, not the state polling loop.
4. **GPU use:** inspect the renderer created by the actual camera/window context.

The shared `multiros-check-rendering --require-accelerated` diagnostic runs
inside a robot image with MuJoCo, NumPy and PyOpenGL. It reports the renderer
and checks textured RGB, known metric depth and segmentation. A working CUDA
probe or a visible GPU device does not establish which renderer that context uses.

If it reports llvmpipe or another software renderer, check the recipe's graphics
override. In the tested WSL setup, native viewing required Mesa D3D12 and access
to `/usr/lib/wsl/lib`; Mr Handy's bootstrap supplies those host settings.

Once acceleration works, compare effects-disabled rendering with the full
preset. The native viewer defaults to `--quality fast`. Robot cameras have
separate settings: changing the viewer does not change camera rendering.
Also close competing GPU workloads during benchmarks.

For a slow simulator, inspect sensor computation as well as image rendering.
A 10 Hz published lidar does not imply that its rays are calculated only 10 times
per second. A passive pose viewer can use `--kinematics-only` to avoid repeating
physics/sensor calculations in its local model copy.

A configured sensor rate is often in simulation time. A simulator running at
half real time will not deliver that rate in wall time. Increasing a browser's
subscription rate cannot fix an already slow camera producer.

## Shutdown or a new launch fails

Use `sim-stop` and let the robot's shutdown hook finish. A new launch may be
rejected while the previous one still owns its session lock. If the shared
shutdown hook fails, the runner leaves the runtime alone; inspect the sim
terminal before trying again.

`logs` follows container output. A foreground simulation launched through
container exec may write to its own terminal rather than the container's main
log stream. The robot may also keep ROS launch logs inside the container.

`down` preserves volumes. Avoid removing them to fix a launch problem unless
you intend to discard the stored build, logs or robot data.
