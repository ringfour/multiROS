# Porting a robot to multiROS

The target layout and decisions are in [shared-core.md](shared-core.md).
This guide describes the migration contract. The source runner, starter,
rendering base and passive MuJoCo frontend exist; see [runner.md](runner.md).
XLeRobot uses the common lifecycle; adapters for other simulator owners remain work.

## Start with the working robot

Write down the commands that currently build and run it. Identify the physics
owner, controller owner, sensor publishers and middleware. Record the package
paths, launch arguments, ports, assets and hardware devices. Choose one small
simulation profile as the first target; leave hardware disconnected.

For a composite robot, record which packages come from which component and the
exact commits being consumed. Keep assembly-specific patches with the assembly.
Do not silently edit an unrelated sibling checkout during setup.

## Make inputs explicit

Pin multiROS from `https://github.com/ringfour/multiROS.git` to a commit. Commit the robot's
Pixi lockfile and exact source dependencies. Record image digests for releases
and checksums for downloaded models, worlds and policies. Provide a deliberate
developer override for local source, and include it in diagnostics.

Use `pixi install --locked` in validation so a stale manifest/lock combination
fails. A lockfile for host tools does not pin apt packages inside the image.

## Put the runtime in Docker

Extend the shared rendering base with robot-specific packages. Keep the
simulator, controllers and sensor rendering in Linux containers. Select a
platform graphics override explicitly; make CPU rendering an explicit fallback.

Keep middleware selection at the robot/profile level. Expose only the required
devices in hardware profiles. A simulation should not require privileged mode,
the host SSH directory, every `/dev` device or a host-wide process-kill command.

Use project-specific Compose names, runtime directories and ports. Stopping a
viewer or one project's session must not stop another robot's processes.

## Add the host tasks

Expose the task contracts in [shared-core.md](shared-core.md#pixi-is-the-host-interface).
Keep task definitions thin and put reusable behavior in the shared runner.
Do not copy another robot's full management script into the new recipe.

The initial environment should only need host tools. Add a separate native
viewer environment with a simulator version compatible with the chosen backend.
Keep any native ROS development environment optional during migration.

## Connect a frontend

For MuJoCo, export state from the existing simulator rather than starting a
second simulation. Supply the same model and assets to the passive viewer.
Validate session/model/version metadata before applying state. Match free-body
poses as well as articulated joints; `/joint_states` alone cannot describe a
mobile base or loose objects.

For Gazebo, use its transport and server/GUI split. Test the server's actual
camera renderer; opening a GUI does not prove that RGB-D works in Docker.

Keep image frames in the container's sensor/ROS path. A host viewer only needs
state for interactive display, plus any sensor streams the user chooses to view.

## Decide when the old recipe can go

Test from a clean checkout without prebuilt sibling install directories. Check
build and startup, actual RGB/depth output, clock and TF, controller readiness,
and a small robot-appropriate movement. For G1 this includes the existing
balance/policy checks; for a bench arm it does not require Nav2.

Close the native viewer and verify simulation and cameras continue. Restart the
simulation and verify the viewer does not apply stale state. Run two projects
and verify stopping one leaves the other running.

Record the OS, CPU architecture, Docker backend, engine versions and actual GL
renderer. Repeat on each platform before calling that profile supported.
Keep GPU and explicit software-fallback results separate.

Retire the old simulation path once these checks pass and its useful commands
are covered. Port hardware separately with its existing watchdogs, device
permissions and command ownership intact.
