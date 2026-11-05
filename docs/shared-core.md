# Shared core and robot ownership

Inspected local repositories on 5 November 2026. Only XLeRobot has been migrated.

| Robot | Existing runtime | Keep robot-specific |
| --- | --- | --- |
| XLeRobotROS | Python MuJoCo owner and separate camera process | LeKiwi integration, models, controllers, cameras and navigation |
| grove-g1 | Unitree C++ MuJoCo and DDS interface | 29-motor owner, balance policy, SDK, hands and sensor relay |
| mr_handy | `mujoco_ros2_control`, composed from base101 and mod101 | Assembly, lifts, tools, world and assembly compatibility patches |
| base101 | Gazebo/MuJoCo simulation; Axon 2 firmware on hardware | Firmware contract, watchdog/time sync, EKF, navigation and optional arms |
| mod101 | Gazebo/MuJoCo bench and real-arm workflows | Arm/tool models, servo configuration, controllers and optional planning |

## What we share

Host commands, container lifecycle, rendering images, diagnostics and passive
frontends belong in multiROS. Robot source layouts and launch files stay intact.
Navigation, MoveIt, perception and the robocore agent remain optional services.

Use a thin template for robot-owned configuration and a commit-pinned multiROS
submodule for shared implementation. The template is copied once; bug fixes
arrive through dependency updates. Do not replace one copied dispatcher with
another robot-specific framework.

The old forge generator has useful build/cache and deployment ideas, but its
configuration language is not required to wrap existing Compose projects.
base101's current hardware documentation supersedes its older forge recipe.

## Constraints the core must preserve

G1 uses ROS Fast DDS because the Unitree SDK carries its own CycloneDDS. Do not
force a global RMW choice. Its learned locomotion controller and motor command
owner must stay intact. The current recipe downloads x86-64 MuJoCo binaries;
Apple Silicon support needs separate work.

base101 hardware no longer uses host-side drive `ros2_control`: firmware owns
locomotion, while the host EKF owns fused odometry. A shared launcher must not
introduce a second owner. mod101 bench deliberately omits navigation and SLAM.

Handy needs pinned component commits. Today its Docker build fetches default
branches. mod101 hardware imports drivers from `main`; base101's native setup
uses sibling simulator and mod101 installs. Replace these ambient dependencies
as each robot is ported.

## Simulator versions and state

Current recipes use different MuJoCo versions: XLeRobot Python 3.13.0,
G1 C++ 3.3.6, and base101/mod101 vendor 3.8.1 with matching Python bindings.
Handy pins Python checks to 3.6.0 but resolves its C++ engine through unversioned
ROS apt packages; its engine version needs auditing.

The shared frontend must work through backend adapters, not replace these
engines. A `mujoco_ros2_control` exporter should expose existing state without
owning physics. G1 needs an equivalent Unitree exporter. mod101's existing
ROS mirror is a useful reference, but requiring host `rclpy` is outside the
portable host contract.

Use a versioned state envelope with session, sequence, model and engine identity.
The current file reader includes an explicit legacy adapter for XLeRobot.
Sockets are the planned remote transport. Camera pixels remain in the container
sensor/ROS path. Gazebo uses its own server/client transport.

## Migration order

1. XLeRobot: common lifecycle and native viewer, with rendering regression checks.
2. mod101 bench: prove a second physics backend and optional navigation/agent.
3. base101 simulation: remove sibling-tool assumptions and test optional arms.
4. Handy: pin component commits and validate the assembled robot.
5. G1: preserve SDK/policy/middleware ownership and validate rendering/architecture.

Port real hardware separately. Retire each old recipe only after a clean
checkout passes that robot's build, sensor and control checks.
