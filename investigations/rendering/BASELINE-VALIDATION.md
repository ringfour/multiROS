Historical record of the baseline and isolated experiment. Current results
are in [VALIDATION.md](../../VALIDATION.md).

# Historical rendering validation — 5 November 2026

Test machine: Apple M4, macOS, lighter 0.13.8, Linux ARM64 containers.
ROS Jazzy and Ubuntu Noble remain the runtime. No host 3D frontend was running
during the live ROS tests.

| Check | Result |
|---|---|
| Shared `multiros:jazzy-lighter` build | Passed |
| EGL/Vulkan device probe | Apple M4 through Venus 25.2.8 and patched Zink 25.1.9 |
| Small accelerated RGB-D scene | RGB, 1.9900 m wall depth and segmentation passed at 640 × 480 |
| Full XLeRobot scene through EGL/Zink | Failed; Metal shader-interface mismatch and Venus abort |
| Same full scene on the original GPUAccelerationTest image | Failed too |
| Standard robot model checks, container OSMesa | Passed |
| Mod101 model checks, container OSMesa | Passed |
| Standard live controllers, synchronized RGB-D, IMU, TF, cloud, RTAB-Map and actions | Passed |
| Mod101 live checks, including both full arms and grippers | Passed |
| Standard and Mod101 dashboard camera previews, pose freshness and controls | Passed with the fast CPU profile |
| Standard Nav2 short goal | Passed |
| Second physics launch during an active session | Rejected; active session preserved |
| Native frontend import in the default Pixi environment | Passed without importing ROS |

## Working configuration

XLeRobot's lighter override explicitly defaults to OSMesa/llvmpipe. Its camera
process runs inside Docker and publishes image arrays directly to ROS. The fast
sensor profile disables multisampling, shadows and reflections. It preserves
640 × 480 resolution, camera calibration, metric depth and robot segmentation.
The observed furnished-world camera rate was approximately 6.5 Hz. The configured
15 Hz remains a target, not an achieved rate.

Before the fast profile, live sensors and controller checks passed, but the
dashboard's one-second pose freshness check failed. With the fast profile, the
standard dashboard check passed without loosening its assertions.

## GPU failure

The host's lighter log reports:

```text
VK_ERROR_INITIALIZATION_FAILED: Render pipeline compile failed
Fragment input(s) user(locn1_3) mismatching vertex shader output type(s)
or not written by vertex shader.
```

This happens on full robot scenes, despite successful rendering of the small
primitive scene. Removing shadows and multisampling did not resolve it.
Disabling asynchronous submission or changing Zink shader compilation options
also did not establish a working full-scene GPU path.

The shared lighter base is useful for reproducing and fixing this failure, but
it is not validated for accelerated XLeRobot cameras. Do not replace the robot's
CPU default with EGL based on the small diagnostic alone. No OpenGL version
override is used to claim unsupported features.

## Limits

These are short simulation checks, not long-run navigation or hardware tests.
RTAB-Map rejected some loop closures during the navigation run. Windows/WSL,
Linux GPU drivers and Gazebo sensor rendering have not been validated. The
native frontend was import-checked, not visually retested in this pass.

## Subsequent candidate fix

The [texture investigation](README.md) reduced the
failure to a textured primitive and tested a targeted Zink shader I/O patch in
`xlerobot:jazzy-lighter-shader-io`. All eight feature cases, 30 full-quality RGB-D
frames, both robot model checks and an isolated synchronized ROS camera probe
passed. Pixel comparisons closely match the CPU reference.

This candidate image does not replace the default rendering base or the running
robot. Live mapping/navigation on the GPU candidate and broader shader coverage
remain to be checked. Shader debug output exposes a separate Metal reserved-name
collision, documented in the report.
