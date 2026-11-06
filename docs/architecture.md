# Architecture

multiROS wraps a robot's existing runtime with shared host commands and passive
viewing. It keeps simulation and sensor rendering in Linux containers so the
host can remain a small development environment.

[← README](../README.md)

## Responsibilities

| Layer | Owns |
| --- | --- |
| multiROS | Host runner, reusable viewer, rendering bases and diagnostics |
| Robot recipe | Pixi tasks, commands, Docker/Compose files, devices, ports and middleware |
| Robot/component packages | Descriptions, controllers, simulator ownership, sensors and launch behavior |
| Native viewer | A read-only display of received model/state |

The shared tool does not choose a universal physics engine or add navigation,
MoveIt or perception to every robot. A bench arm, a mobile base and a complete
assembly can expose different tasks through the same host interface.

## Runtime and state

Docker Compose is used on the tested macOS and WSL setups. The experimental
WSLC adapter handles native Windows separately; see [Platforms](platforms.md).
multiROS owns base images and reusable platform graphics profiles. A robot
selects those profiles and owns its runtime image, packages, launch commands,
ports and data. Platform settings still need an actual rendering check.

Keep one physics/control owner. XLeRobot has a Python simulator; Mr Handy uses
C++ `mujoco_ros2_control`. Their native viewers consume state from those owners.
The host does not generate sensor images and send them back to ROS.

The current MuJoCo transport is a local atomic snapshot file. It includes engine,
model and session identity in schema 1, with an explicit legacy option for older
exporters. [Simulation and viewing](simulation.md) documents the contract.
Remote transport and restartable physics checkpoints are separate work.

## Integrations

| Robot | Runtime ownership | Shared integration |
| --- | --- | --- |
| XLeRobotROS | Python physics and a separate camera process | Runner and passive XML/legacy-state viewer |
| Mr Handy | C++ ros2_control, assembled from base101/mod101 | Runner, complete-state export and passive MJB/schema-1 viewer |

Mr Handy keeps its existing startup script for asset preparation and its Zenoh
router. Its state-export plugin observes the simulator; it does not replace the
hardware system or camera plugin. Component source pinning remains a separate
recipe concern: Handy's BuildKit contexts still resolve default branches.

For other backends, preserve their existing boundaries during integration:

- Unitree/G1 needs its motor/policy owner and SDK middleware compatibility intact.
- Base101 hardware keeps firmware-owned locomotion and host-owned fused odometry.
- Mod101 bench workflows should not acquire navigation or SLAM as a side effect.
- Gazebo keeps its server/client transport and server-side sensors.

A portable host workflow does not by itself validate hardware devices, USB
passthrough, a new simulator version or a different GPU driver.

## Reproducibility and validation

Pin multiROS as a submodule and commit each recipe's host lockfile. Pin component
sources and assets deliberately; retain release images by digest when required.
Source commits and Pixi locks do not freeze OS package repositories.

A robot integration should be exercised without ambient sibling install trees.
Check build/startup, real sensor output, clock, TF, controller ownership and a
small robot-appropriate motion. Closing a viewer must leave sensors running;
stopping one project must leave others alone. The
[validation record](../VALIDATION.md) separates tested profiles from future work.
