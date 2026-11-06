# Validation

This page records what was exercised, on which setup, and what remains open.
Use [Getting started](docs/getting-started.md) for setup instructions and
[Platforms](docs/platforms.md) to choose a runtime.

## Current coverage

| Setup | Exercised | Limits |
| --- | --- | --- |
| Apple M4 / macOS / lighter | XLeRobot, GPU RGB-D and native viewer | Long-run navigation and other macOS architectures remain separate |
| WSL2 / Docker Desktop / Intel D3D12 | XLeRobot and Mr Handy simulation, sensors and host viewing | Results are specific to the tested recipes/driver |
| Windows-native viewer | XLeRobot viewing from WSL files | Does not validate the WSLC container adapter |
| Native Linux / DRM or NVIDIA | Command/backend configuration | GPU integration runs still pending |
| Native Windows / WSLC | Command-planning tests | Live container/GPU run still pending |

The recent WSL results include local integration changes. They record tested
working checkouts, not a published release or a frozen OS dependency set.

## WSL and Docker Desktop

Tests on 5–6 November 2026 used Ubuntu WSL2, Docker Desktop and Intel UHD Graphics
770 through Mesa D3D12. XLeRobot used MuJoCo 3.13.0. Mr Handy's C++ vendor,
Python checks and native viewer were aligned to MuJoCo 3.12.0.

- Shared runner/viewer tests passed, including literal arguments, project
  isolation, shutdown handling, schema validation, embedded MJB assets and
  display-kinematics equivalence. The updated suite has 22 tests; viewer tests
  require the optional dependencies.
- XLeRobot's standard and Mod101 model checks passed. The small accelerated
  rendering diagnostic passed RGB, 1.9900 m depth and segmentation. Live sensor,
  TF and mapping checks passed, while an arm-trajectory tolerance check failed
  on the existing image; this is not a blanket live-control pass.
- Mr Handy's description/physics and live checks passed for 22 joints, all six
  trajectory actions, TF, drive routing, three RGB-D cameras, lidar, IMU and
  browser HTTP/WebSocket feedback. Its schema-1 export included the complete
  free-base/prop state. A short navigation goal passed from a clear initial pose.
- An extended Handy wrist contacted a prep table during navigation after joint
  tests. Its inherited chassis-only navigation footprint does not protect raised
  arms; this remains a robot-level limitation.

With Handy's fast camera preset and 100 Hz lidar sampling, physics reached real
time and all three 640×480 cameras reached their configured 5 Hz. The native WSL
window averaged about 14–15 FPS in later game-closed measurements with the camera
stack running. Competing GPU workloads materially changed those results.

The shared [WSL comparison data](investigations/rendering/wsl-desktop-2026-11-05.json)
records a separate effects-disabled viewer comparison. Robot-specific changes,
conditions and full results are recorded in the
[XLeRobot performance guide](https://github.com/cristidragomir97/XLeRobotROS/blob/main/docs/wsl-performance.md)
and [Mr Handy performance guide](https://github.com/cristidragomir97/mr_handy/blob/main/docs/wsl-performance.md).

## Earlier macOS validation

The 5 November 2026 Apple M4 run used lighter 0.13.8, Docker 28.3.3, ROS Jazzy
and MuJoCo 3.13.0. At that revision:

- All 20 then-existing runner/snapshot tests passed, including WSLC planning,
  argument handling and project-scoped shutdown behavior.
- Locked host dependency installation passed. The starter's Compose file was
  validated from a path with spaces, and overwrite rejection was checked.
- Both XLeRobot model configurations and its three dashboard configuration tests
  passed. The shared native viewer and standalone example opened successfully.
- The textured RGB/reference-depth/segmentation diagnostic reported accelerated
  Zink/Venus/MoltenVK rendering on Apple M4. Mesa feature warnings remained.
- Earlier live XLeRobot runs passed controls, sensors/TF, dashboard actions,
  watchdog and a short navigation goal. Camera output was roughly 13–14 Hz at
  640×480 against a 15 Hz target, with mapping and viewing active.

The shared lighter image contains the shader I/O and Metal resource-name fixes.
The textured reproducer, feature cases and full scenes passed that patched path.
The [rendering investigation](investigations/rendering/README.md) preserves the
original failure, experiments and attribution.

## Still to validate

Native Linux GPU backends, the WSLC runtime, Gazebo cameras and other robot
backends need dedicated runs. Real hardware, long-duration navigation and
remote state transport are separate from these simulation checks.

XLeRobot still uses legacy display snapshots, so its frontend cannot verify
engine/model/session identity. Handy uses schema 1. Neither format is a
restartable physics checkpoint.

Source pins and host locks do not freeze apt repositories or mutable image tags.
No release image digest or frozen apt snapshot is supplied by this record.
