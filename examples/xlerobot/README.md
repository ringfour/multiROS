# XLeRobot integration

[XLeRobotROS](https://github.com/cristidragomir97/XLeRobotROS) pins multiROS at
`tools/multiros`. Its Pixi tasks call a small Python bootstrap; runtime behavior
lives in the shared runner. There is no robot management shell dispatcher.

`multiros.json` declares Compose overrides, WSLC mounts/environment, source
modules, colcon packages, robot commands and viewer options. The default host
environment contains Python only; the optional viewer environment pins MuJoCo
3.13.0. `MULTIROS_ROOT` is an explicit source-development override.

Physics, camera rendering and ROS remain unchanged in the container. The host
frontend tracks the robot's `chassis` body and hides collision geometry. It
explicitly accepts the existing legacy snapshots until the exporter is updated.

Use XLeRobot's [README](https://github.com/cristidragomir97/XLeRobotROS) for the
current commands and Windows test procedure.
