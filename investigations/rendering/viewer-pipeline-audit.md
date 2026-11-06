# Viewer pipeline audit

Reviewed on WSL/Docker Desktop, Intel UHD 770, XLeRobot / MuJoCo 3.13.0,
6 November 2026. Shared camera-control helpers also pass CPU tests on 3.12.0.
The new GLFW window has only been exercised on WSL; other platform defaults
are unchanged.

The old native window consumes a small state snapshot, not raw camera pixels.
Its repeating costs are in the 3D renderer and synchronization. The dashboard
already sends JPEG previews over WebSocket. RGB transport inside ROS was raw
and is now a separate standard `sensor_msgs/CompressedImage` topic in XLeRobot.
Metric RGB-D mapping inputs remain unchanged; depth previews keep their existing
JPEG browser path and depth-range metadata.

## Source findings

MuJoCo's pinned [passive render loop](https://github.com/google-deepmind/mujoco/blob/3.13.0/simulate/simulate.cc)
updates and draws on its own thread. The host script's sleep only controls sync
calls. Default sync copies visual model/data arrays; state-only sync instead
copies integration state and runs forward calculations. Mesh parsing/upload is
not repeated on every sync. We measured about 8.5–8.8 ms per sync in the full UI,
versus about 0.4 ms loading snapshots. Pixel compression cannot remove this work.

## Changes

The shared optional GLFW frontend uses one model/data pair and one event/render
loop. Its budget caps actual drawing. XLeRobot's WSL recipe selects 15 FPS,
1280×720 and kinematics-only transforms; full UI is still explicitly available.
A rigid-scene cache excludes hidden contact geoms and includes visible poses,
tracked/fixed cameras and lights. Input/exposure/resize force redraws, minimized
windows skip drawing, and deformables conservatively bypass reuse. The strict
1e-5 visible-pose tolerance does not alter physics or camera measurements.
Frozen-state smoke tests verify reuse, visible motion redraw, orbit/zoom and
read-only state. Unit tests verify hidden-joint filtering, moving lights and
camera controls on MuJoCo 3.12/3.13.

The default XLeRobot dashboard now subscribes to JPEG RGB instead of receiving
raw ROS RGB and encoding it itself. The source encodes only with subscribers;
the bridge passes its JPEG bytes through unchanged, covered by a regression
test. Image publisher history is one frame and unused raw planes are not copied
into messages. Depth/SLAM data are not replaced by lossy JPEG.

## Measured limits

Four live samples in passive, GLFW, GLFW, passive order gave:

| | Passive full UI | GLFW, capped at 15 FPS |
| --- | --- | --- |
| Viewer CPU, percent of one core | 56.8–58.6% | 14.5–15.0% |
| Camera delivery | 7.91–7.94 Hz | 8.87–9.01 Hz |
| Median image age | 140 ms | 130 ms |
| Physics real-time factor | 1.000–1.001 | 1.000 |

The full-UI default window and the 1280×720 lightweight window differ, so this
compares complete frontend configurations rather than isolating each mechanism.
Both runs requested compressed RGB: 15.3–15.4 KB median versus 921.6 KB raw, about
60 times smaller for this view. That byte comparison does not establish a CPU
speedup from JPEG. All current live GLFW samples still drew at the cap: their
visible poses changed above the strict tolerance. No idle-frame saving is claimed
for those samples. Passive sync counts are not rendered FPS.

The raw profiles are in XLeRobotROS at
`docs/wsl-viewer-frontends-2026-11-06.json`. These are short stationary-scene
samples, not long-run navigation or a claim about discrete GPUs/macOS/WSLC.
