"""Extract the ocean-colored logo from the failed opaque checkerboard edit.

Usage: python scripts/extract-logo.py INPUT OUTPUT
Requires Pillow, NumPy, SciPy. This is an optional asset tool, not a runtime dependency.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage as ndi

source = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(np.float32)
chroma = source.max(axis=2) - source.min(axis=2)
teal = (source[:, :, 1] - source[:, :, 0] > 15) & (chroma > 20)
labels, _ = ndi.label(teal)
sizes = np.bincount(labels.ravel())
keep = sizes >= 200
keep[0] = False
teal = keep[labels]

# Preserve bright seafoam embedded in the logo, without keeping the gray tiles.
near_art = ndi.distance_transform_edt(~teal)
foam = (source.min(axis=2) > 222) & (near_art < 8)
mask = ndi.binary_closing(teal | foam, iterations=1)
holes = ndi.binary_fill_holes(mask) & ~mask
hole_labels, _ = ndi.label(holes)
hole_sizes = np.bincount(hole_labels.ravel())
small_holes = hole_sizes < 900
small_holes[0] = False
mask |= small_holes[hole_labels]

# A subpixel edge keeps the extracted asset smooth at header and hero sizes.
alpha = np.asarray(Image.fromarray((mask * 255).astype('uint8')).filter(ImageFilter.GaussianBlur(.5))).copy()
alpha[alpha < 8] = 0
# Prevent the old gray background from contaminating antialiased edge pixels.
_, nearest = ndi.distance_transform_edt(~mask, return_indices=True)
edge = (alpha > 0) & ~mask
source[edge] = source[nearest[0][edge], nearest[1][edge]]
rgba = np.dstack([source.astype('uint8'), alpha])
logo = Image.fromarray(rgba)
bounds = logo.getbbox()
if bounds is None:
    raise ValueError('No logo foreground detected')
logo = logo.crop(bounds)
padding = round(logo.width * .018)
output = Image.new('RGBA', (logo.width + padding * 2, logo.height + padding * 2))
output.alpha_composite(logo, (padding, padding))
Path(sys.argv[2]).parent.mkdir(parents=True, exist_ok=True)
output.save(sys.argv[2], optimize=True)
print(f'Saved {sys.argv[2]}: {output.size}, {output.mode}, alpha {output.getchannel("A").getextrema()}')
