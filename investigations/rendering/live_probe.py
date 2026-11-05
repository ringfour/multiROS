#!/usr/bin/env python3
"""Check synchronized ROS camera output in the isolated candidate container."""
import time
import numpy as np
import rclpy
from sensor_msgs.msg import Image, CameraInfo
from rclpy.qos import qos_profile_sensor_data

rclpy.init()
node = rclpy.create_node('multiros_gpu_camera_probe')
frames = {'rgb': [], 'depth': [], 'info': []}
messages = {}
def receive(key, message):
    stamp = message.header.stamp
    frames[key].append((time.monotonic(), stamp.sec, stamp.nanosec))
    messages[key] = message
subscriptions = []
for key, kind, topic in [('rgb', Image, '/camera/color/image_raw'),
                         ('depth', Image, '/camera/aligned_depth_to_color/image_raw'),
                         ('info', CameraInfo, '/camera/color/camera_info')]:
    subscriptions.append(node.create_subscription(kind, topic, lambda msg, k=key: receive(k, msg), qos_profile_sensor_data))
try:
    deadline = time.monotonic() + 40
    while len(messages) < 3 and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=.1)
    assert len(messages) == 3, messages.keys()
    started = time.monotonic()
    while time.monotonic() - started < 10:
        rclpy.spin_once(node, timeout_sec=.1)
    stamps = [{row[1:] for row in frames[key]} for key in frames]
    assert len(set.intersection(*stamps)) >= 10
    rgb, depth, info = messages['rgb'], messages['depth'], messages['info']
    assert (rgb.width, rgb.height, rgb.encoding) == (640, 480, 'rgb8')
    assert (depth.width, depth.height, depth.encoding) == (640, 480, '32FC1')
    assert len(rgb.data) == 640 * 480 * 3 and len(depth.data) == 640 * 480 * 4
    pixels = np.frombuffer(bytes(depth.data), dtype='<f4')
    assert np.isfinite(pixels).all() and np.any(pixels > .15)
    assert rgb.header.frame_id == depth.header.frame_id == info.header.frame_id == 'head_camera_rgb_optical_frame'
    rates = {key: (len(rows) - 1) / (rows[-1][0] - rows[0][0]) for key, rows in frames.items()}
    print('PASS: live synchronized RGB-D and calibration from the isolated GPU candidate', flush=True)
    print('Observed wall-clock rates:', rates, flush=True)
finally:
    node.destroy_node()
    rclpy.shutdown()
