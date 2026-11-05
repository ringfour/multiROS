# Shared MuJoCo frontend

`multiros.viewer` consumes a scene and snapshots. It calls `mj_forward` for
display, never `mj_step`. It has no ROS dependency or robot-specific imports.

Inspect the small included scene:

```bash
pixi run -e mujoco example-view
```

To follow an exporter, launch the module with the Python environment's
`mjpython` on macOS, or `python` on Linux/Windows:

```bash
mjpython -m multiros.viewer --runtime /path/to/shared-runtime
```

The runtime must contain `scene.xml`, its referenced assets, and `viewer.npz`.
The existing physics owner publishes the state. No host ROS installation is
needed. A remote simulator will need a network state-source adapter; the first
implementation reads atomic local snapshots only.

## Display snapshot schema 1

Publish these fields using NumPy `savez`, with no pickle/object arrays:

| Field | Meaning |
| --- | --- |
| `schema` | Scalar integer `1` |
| `session` | Nonempty string identifying this simulator run |
| `sequence` | Nonnegative integer increasing within the session |
| `model_sha256` | SHA-256 of the exact scene XML bytes loaded by the viewer |
| `mujoco_version` | Exact Python-compatible engine version string |
| `time` | Finite scalar simulation time |
| `qpos`, `qvel`, `ctrl` | Finite numeric arrays matching this model's dimensions |

Write to a unique temporary file in the same directory, close it, then replace
`viewer.npz` atomically. The exporter owns publication rate and simulator access;
do not read mutable physics state from another thread without synchronization.

The reader validates every array before changing display state. It rejects a
different model/version, a repeated or older sequence, and a session change.
Restart the viewer to attach to a new session. The first snapshot establishes
the session; checking that a producer is currently alive still belongs to the
adapter. An abandoned file can otherwise appear valid on initial attachment.

The scene hash identifies XML bytes, not the transitive mesh/texture contents.
Keep assets immutable and pin/checksum them with the robot release. This format
is for visualization; it is not a complete checkpoint or sensor-rendering state
contract. Additional MuJoCo state may be needed for those uses.

`--legacy-snapshots` accepts the old time/qpos/qvel/ctrl format for incremental
migration. It validates dimensions and finite values but cannot establish
session, model or engine identity. XLeRobot currently uses this adapter.

The next adapter should export state from `mujoco_ros2_control` while retaining
its existing physics/control owner. The Unitree backend follows the same rule.
