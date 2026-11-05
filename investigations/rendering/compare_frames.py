#!/usr/bin/env python3
"""Compare two backend captures made from exactly the same simulation state."""
import argparse
import json
from pathlib import Path
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--reference', type=Path, required=True)
parser.add_argument('--candidate', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
with np.load(args.reference / 'state.npz') as a, np.load(args.candidate / 'state.npz') as b:
    assert set(a.files) == set(b.files)
    for name in a.files:
        assert np.array_equal(a[name], b[name]), f'Different simulation state: {name}'
with np.load(args.reference / 'pixels.npz') as a, np.load(args.candidate / 'pixels.npz') as b:
    for name in ('rgb', 'depth', 'segmentation'):
        assert a[name].shape == b[name].shape, name
    rgb = np.abs(a['rgb'].astype(float) - b['rgb'].astype(float))
    depth = np.abs(a['depth'] - b['depth'])
    agreement = (a['segmentation'] == b['segmentation']).all(axis=2)
    result = {'rgb_mean_absolute_error_0_255': float(rgb.mean()),
              'rgb_p99_absolute_error': float(np.percentile(rgb, 99)),
              'depth_median_absolute_error_m': float(np.median(depth)),
              'depth_p99_absolute_error_m': float(np.percentile(depth, 99)),
              'segmentation_pixel_agreement': float(agreement.mean())}
args.output.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
