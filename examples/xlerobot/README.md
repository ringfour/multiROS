# XLeRobot integration

[XLeRobotROS](https://github.com/cristidragomir97/XLeRobotROS) uses a pinned
`tools/multiros` checkout behind robot-owned Pixi tasks and a small bootstrap.
Its `pixi.toml` declares container settings, sources, builds and commands.

The robot keeps Python physics, camera rendering, controllers and navigation
inside Docker. The native viewer follows its `chassis` body, hides collision
geometry and currently opts into the legacy snapshot adapter. Its viewer
environment pins MuJoCo 3.13.0.

Use the robot's README for its launch options, dashboard and checks. For the
shared pattern, read [Getting started](../../docs/getting-started.md),
[Configuration](../../docs/configuration.md) and
[Simulation and viewing](../../docs/simulation.md).

`MULTIROS_ROOT` lets its bootstrap test a deliberate local core override;
`doctor` reports that checkout's path and revision.
