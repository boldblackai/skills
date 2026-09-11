#!/usr/bin/env python3
"""Remove a solid background from an image via chroma keying.

Two modes:
  --mode magenta  (default for magenta/#FF00FF backgrounds)
  --mode luminance (for dark solid backgrounds; samples corners for ref color)

Magenta mode keys on chroma (R>200, G<40, B>200) — robust against slight
background noise/dithering since it separates by color, not brightness.
Luminance mode keys on brightness relative to the sampled background — works
for dark backgrounds but can eat into dark subjects (use magenta instead when
possible).

Both modes feather the alpha at the boundary (anti-alias band) for smooth edges.

Usage:
    python3 make_transparent.py input.png --output output.png
    python3 make_transparent.py input.png --output output.png --mode luminance
    python3 make_transparent.py input.png --output output.png --resize 64
"""

import argparse
import sys
from collections import Counter

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Install with: uv pip install Pillow", file=sys.stderr)
    sys.exit(1)


def key_magenta(px, w, h):
    """Key out magenta (#FF00FF) background by chroma separation."""
    out_alpha = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            if r > 200 and g < 40 and b > 200:
                out_alpha[y * w + x] = 0  # transparent
            elif r < 100 or g > 100:
                out_alpha[y * w + x] = 255  # opaque (book/green)
            else:
                # Anti-alias band: feather by R channel
                a = int(255 * (200 - r) / 100)
                out_alpha[y * w + x] = max(0, min(255, a))
    return out_alpha


def key_luminance(px, w, h, bg_lum=37, threshold=44, feather_hi=52):
    """Key out a dark solid background by luminance, preserving colored pixels."""
    out_alpha = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            lum = (r + g + b) // 3
            greenish = (g > r + 10) and (g > b + 5)

            if lum <= threshold and not greenish:
                if lum <= bg_lum:
                    out_alpha[y * w + x] = 0
                else:
                    # Feather between bg_lum and threshold
                    a = int(255 * (lum - bg_lum) / (threshold - bg_lum))
                    out_alpha[y * w + x] = max(0, min(255, a))
            elif lum <= feather_hi and not greenish:
                a = int(255 * (lum - threshold) / (feather_hi - threshold))
                out_alpha[y * w + x] = max(0, min(255, a))
            else:
                out_alpha[y * w + x] = 255
    return out_alpha


def sample_bg_luminance(px, w, h):
    """Sample background luminance from corners."""
    lums = []
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
                 (w // 2, 0), (0, h // 2), (w - 1, h // 2)]:
        r, g, b = px[x, y][:3]
        lums.append((r + g + b) // 3)
    return min(lums)  # conservative: darkest corner


def main():
    parser = argparse.ArgumentParser(description="Chroma-key background removal")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("--output", required=True, help="Output PNG path (RGBA)")
    parser.add_argument("--mode", choices=["magenta", "luminance"], default="magenta",
                        help="Keying mode (default: magenta)")
    parser.add_argument("--resize", type=int, help="Optional: resize to NxN (e.g. 64)")
    args = parser.parse_args()

    im = Image.open(args.input).convert("RGB")
    w, h = im.size
    px = im.load()

    if args.mode == "magenta":
        alpha = key_magenta(px, w, h)
    else:
        bg_lum = sample_bg_luminance(px, w, h)
        print(f"Sampled background luminance: {bg_lum}", file=sys.stderr)
        alpha = key_luminance(px, w, h, bg_lum=bg_lum)

    # Build RGBA output
    out = Image.new("RGBA", (w, h))
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            op[x, y] = (r, g, b, alpha[y * w + x])

    if args.resize:
        out = out.resize((args.resize, args.resize), Image.LANCZOS)

    out.save(args.output)

    # Stats
    c = Counter(alpha[y * w + x] for y in range(0, h, 4) for x in range(0, w, 4))
    transparent = c.get(0, 0)
    opaque = c.get(255, 0)
    partial = sum(v for k, v in c.items() if 0 < k < 255)
    total = transparent + opaque + partial
    print(f"Saved: {args.output}", file=sys.stderr)
    print(f"Transparent: {transparent} ({100*transparent/total:.1f}%)  "
          f"Opaque: {opaque} ({100*opaque/total:.1f}%)  "
          f"Feathered: {partial} ({100*partial/total:.1f}%)", file=sys.stderr)


if __name__ == "__main__":
    main()
