# Validation

Tested on 5 November 2026 on Apple M4/macOS, lighter 0.13.8,
Docker 28.3.3, ROS Jazzy and MuJoCo 3.13.0.

## Shared workflow cleanup

- All 20 runner/snapshot tests passed, including WSLC command planning, literal
  arguments, project isolation, environment parsing and shutdown-before-replace.
- Locked Pixi installation passed in both repositories. Host dependencies resolve
  for macOS ARM/Intel, Linux ARM/x86-64 and Windows x86-64; only macOS was executed.
- The generated starter passed Compose configuration validation from a path
  containing spaces. Existing-file overwrite rejection is tested.
- Both XLeRobot model configurations passed through the replacement runner.
- All three XLeRobot dashboard configuration unit tests passed.
- The GPU diagnostic passed textured RGB, 1.9900 m reference depth and
  segmentation through the replacement command path. The renderer was
  Zink/Venus/MoltenVK on Apple M4. Existing Mesa feature warnings remain.
- `pixi run view` opened the shared frontend against the live robot after moving
  MuJoCo into its optional host environment. The independent example also opened.
  Closing probe viewers left the external simulator running. Pixel equivalence
  was not measured in this frontend extraction check.

The runtime adapter and Windows dependency lock are ready for manual WSLC
validation. No Windows machine was used here. GPU access, EGL/D3D12, mounts,
asset paths and sensor/control behavior on Windows remain unvalidated.

## Rendering integration

The shared lighter image carries screen-scoped shader I/O and Metal resource-name
fixes. The textured reproducer, eight feature cases and full robot scenes passed
with those fixes. See the [investigation](investigations/rendering/README.md)
for CPU/GPU comparisons and the original failures.

Earlier live XLeRobot checks passed controllers, sensors/TF, dashboard actions,
watchdog and a short navigation goal. The camera produced roughly 13–14 Hz at
640×480 with mapping and a native frontend active, against a configured 15 Hz
target. Long-run navigation and full GPU live Mod101 remain separate validation.

## Remaining scope

Other robot repositories have not been migrated. Linux GPU drivers, Windows
runtime behavior and Gazebo cameras need platform tests. XLeRobot still opts
into legacy snapshots; those cannot establish engine/model/session identity.
Remote state transport and the Unitree/ros2_control exporters are future work.

Robot source pins and Pixi locks are recorded in Git. No release image digest
or frozen apt repository snapshot is supplied, so future source rebuilds can
still resolve different OS dependencies.
