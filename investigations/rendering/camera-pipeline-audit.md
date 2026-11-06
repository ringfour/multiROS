# MuJoCo camera pipeline audit

Reviewed 6 November 2026: XLeRobot, Mr Handy and the shared passive viewer.
Simulations remained stopped. This combines source review, earlier live results
and CPU-only inspection of the saved Mr Handy model. Proposed changes below
are not measured speedups.

## Is the architecture correct?

Yes: one physics owner, persistent rendering resources, rendering at sensor
rates and a separate passive viewer. There is still avoidable integration work.
We have not established that MuJoCo, WSL or Intel alone explains the slowdown.

MuJoCo's [official recording example](https://github.com/google-deepmind/mujoco/blob/3.12.0/sample/record.cc)
creates resources once, renders once and reads RGB/depth together. The
[visualization guide](https://mujoco.readthedocs.io/en/3.12.0/programming/visualization.html)
separates scene construction from GPU rendering and context asset uploads.

Mr Handy's [upstream camera plugin 0.1.2](https://github.com/ros-controls/mujoco_ros2_control/blob/0.1.2/mujoco_ros2_control_plugins/src/camera_plugin.cpp)
already uses persistent resources, a rendering thread, one draw and combined
RGB/depth readback per camera. It converts depth and flips rows on the CPU.
The camera path does not call `mj_forward`.

DeepMind's [dm_control renderer](https://github.com/google-deepmind/dm_control/blob/main/dm_control/mujoco/engine.py)
exposes separate color/depth/segmentation modes; calling all three repeats GPU
work. The [ubi-agni ROS renderer](https://github.com/ubi-agni/mujoco_ros_pkgs/blob/main/mujoco_ros/src/rendering/render_backend.cpp)
combines RGB/depth and handles segmentation separately, supporting the two-pass
approach already implemented for XLeRobot.

## Why Gazebo can behave better

Gazebo's [RGB-D sensor](https://github.com/gazebosim/gz-sensors/blob/main/src/RgbdCameraSensor.cc)
skips rendering without image/point-cloud consumers and publishes requested
outputs. Its [Ogre2 camera](https://github.com/gazebosim/gz-rendering/blob/main/ogre2/src/Ogre2DepthCamera.cc)
has a retained rendering pipeline and GPU readback machinery. RGB-D still costs
rendering and CPU transfers, but more scheduling policy is supplied for you.
These are reference implementations, not verified versions of the user's old
Gazebo installation. A fair engine comparison needs identical scenes, effects,
camera rates, resolutions and hardware.

## Evidence from our code and measurements

| Finding | Evidence | Interpretation |
|---|---|---|
| Repeated XLeRobot draws | Frozen scene: three passes 121.25 ms; two passes 82.5 ms | Already fixed a real inefficiency |
| Compatibility NPZ image transport | Earlier write 1.61 ms; read 0.36 ms | Not the dominant cost in that sample |
| Always-on cameras | Mr Handy renders configured streams regardless of subscribers; XLeRobot also produces every plane | Unused cameras/outputs still cost work |
| Alias subscriptions | Mr Handy subscribes twice to base RGB and twice to depth; forwarding does not check alias consumers | Creates artificial demand and extra publication |
| Full viewer synchronization | Default `sync()` each loop; isolated model-copy median 8.70 ms, data-copy 0.082 ms | Worth testing state-only sync and skipping unchanged states |
| Visual complexity | 476 geoms, four lights, 1,042,049 unique mesh triangles; visible mesh instances total 1,132,415 triangles | Test simplified visual meshes while preserving collisions |
| Hardware | Windows reports Intel UHD 770; WSL rendering uses Intel/D3D12 | No evidence of an accessible discrete GPU being bypassed |

The 112 mesh instances counted above have nonzero alpha and geom groups 0–2.
This is an inventory before camera culling, not measured rasterization work.
Texture storage is 67,239,936 bytes. The approximately 247 MiB MJB embeds assets;
it is not copied in full every viewer frame.

At 640×480 an RGB-D pair contains 2,150,400 uncompressed bytes. Two alias copies
at 5 Hz represent 21.5 MB/s of extra published image payload before overhead.
This is configuration arithmetic, not a measured network transfer rate.

The viewer-copy benchmark used MuJoCo 3.12.0 C functions through ctypes, two
loaded models/data objects and 100 repetitions without graphics or physics
stepping. Model-copy p95 was 9.45 ms. This isolated CPU cost is not an end-to-end
FPS improvement. The [passive viewer docs](https://mujoco.readthedocs.io/en/3.12.0/python.html#passive-viewer)
explain that `sync(state_only=True)` avoids full model sync but calls
`mj_forward` internally. We must check sensors, visualization and model updates
rather than blindly replacing the current kinematics-only path.

Earlier Mr Handy live results with Fortnite closed were 14.25–14.60 native
viewer FPS, real-time physics and about 5 Hz per camera. Five Hz is the configured
target, not an established engine limit. Smaller viewer windows barely changed
FPS; that alone does not distinguish geometry, CPU and GPU bottlenecks.

## Corrections and source risks

The upstream 0.1.2 camera plugin already resizes its framebuffer to the largest
camera. Our initial 640×480 model allocation is not a proven per-frame speedup
over the old 1600×1200 setting. Disabling MSAA, shadows and reflections is a
separate change. Removing obsolete GoPro configuration also did not eliminate
a fourth working camera; the original runtime registered three.

Upstream 0.1.2 has a snapshot ownership risk: the producer copies shared camera
data under a mutex, but the rendering thread unlocks before consuming the same
data and plain `render_pending` flags. A producer update can overlap rendering.
This is source-review evidence, not an observed corrupt frame or race-detector
result. Verify the installed package matches the tag before patching. Prefer a
render-owned immutable snapshot or bounded exchange over locking physics across
GPU work. Three sequential camera renders can also produce increasing delivery
ages, without proving the cost of any particular stage.

## Recommended implementation order

1. Make alias forwarding demand-aware, then gate each camera/output by real
   demand. Preserve an explicit always-on mode for recording and diagnostics;
   camera-info subscribers alone should not trigger image rendering.
2. Measure viewer sync independently from drawing. Compare state-only sync and
   skipping unchanged snapshots, checking sensors and model updates. Keep a
   latest-state handoff rather than accumulating stale poses.
3. Instrument snapshot copy, scene update, GPU draw, readback, conversion and ROS
   publication. Use GPU timers/fences where supported; CPU draw-call timing alone
   does not isolate asynchronous GPU cost.
4. Compare one/three cameras, 5/15/30 Hz, viewer closed/open, fast/standard effects
   and original/simplified visual meshes. Record achieved rate, frame age,
   physics real-time factor and the actual graphics backend.
5. Consider batched rendering/asynchronous readback after identifying the limiting
   stage. Replacing the ROS control stack is not justified by this review.

The latest [MuJoCo rendering guide](https://mujoco.readthedocs.io/en/latest/programming/rendering.html)
recommends Filament for new applications. It is not a toggle for this stack:
the installed Mr Handy 3.12.0 wheel has helper Python files but no importable
`_render_filament` extension. It needs packaging and RGB/depth validation before
benchmarking. No performance improvement is assumed.
