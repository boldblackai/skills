#!/usr/bin/env python3
"""Generate images via OpenRouter Image API.

Reads OPENROUTER_IMAGE_API_KEY from the environment (regular env passthrough).

Usage:
    python3 generate.py "a cyberpunk cat in neon rain" [--model MODEL] [--resolution RES] [--aspect-ratio AR] [--n N] [--output PATH] [--quality Q] [--output-format FMT]

Prints saved file path(s) to stdout. Errors to stderr with non-zero exit.
"""

import argparse
import base64
import os
import sys
import time
import urllib.request
import urllib.error
import json

API_URL = "https://openrouter.ai/api/v1/images"
DEFAULT_MODEL = "openai/gpt-5-image-mini"
DEFAULT_CACHE_DIR = os.path.expanduser("~/.hermes/image_cache")


def _load_api_key() -> str:
    """Load OPENROUTER_IMAGE_API_KEY from the environment."""
    key = os.environ.get("OPENROUTER_IMAGE_API_KEY", "")
    if key:
        return key
    print(
        "ERROR: OPENROUTER_IMAGE_API_KEY not found in environment. "
        "Add it to ~/.hermes/.env.",
        file=sys.stderr,
    )
    sys.exit(1)


def generate_image(
    prompt: str,
    model: str = DEFAULT_MODEL,
    resolution: str | None = None,
    aspect_ratio: str | None = None,
    n: int = 1,
    quality: str | None = None,
    output_format: str = "png",
    output_dir: str = DEFAULT_CACHE_DIR,
) -> list[str]:
    """Call OpenRouter Image API and save results to disk. Returns list of file paths."""

    api_key = _load_api_key()

    payload: dict = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "output_format": output_format,
    }
    if resolution:
        payload["resolution"] = resolution
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if quality:
        payload["quality"] = quality

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")

    print(f"Generating {n} image(s) with {model}...", file=sys.stderr)

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if "error" in resp_data:
        err = resp_data["error"]
        print(f"API error: {err.get('message', err)}", file=sys.stderr)
        sys.exit(1)

    images = resp_data.get("data", [])
    if not images:
        print("ERROR: No images returned in response.", file=sys.stderr)
        sys.exit(1)

    usage = resp_data.get("usage", {})
    cost = usage.get("cost")
    if cost is not None:
        print(f"Cost: ${cost:.4f}", file=sys.stderr)

    os.makedirs(output_dir, exist_ok=True)
    saved_paths = []
    timestamp = int(time.time())

    for i, img in enumerate(images):
        b64_data = img.get("b64_json")
        if not b64_data:
            print(f"WARNING: Image {i} has no b64_json, skipping.", file=sys.stderr)
            continue

        media_type = img.get("media_type", f"image/{output_format}")
        ext = media_type.split("/")[-1] if "/" in media_type else output_format
        if ext == "svg+xml":
            ext = "svg"

        filename = f"{timestamp}_{i}.{ext}"
        filepath = os.path.join(output_dir, filename)

        try:
            image_bytes = base64.b64decode(b64_data)
            with open(filepath, "wb") as f:
                f.write(image_bytes)
            saved_paths.append(filepath)
        except Exception as e:
            print(f"ERROR saving image {i}: {e}", file=sys.stderr)
            sys.exit(1)

    return saved_paths


def main():
    parser = argparse.ArgumentParser(description="Generate images via OpenRouter")
    parser.add_argument("prompt", help="Text description of the desired image")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Model slug (default: {DEFAULT_MODEL})")
    parser.add_argument("--resolution", help="Resolution tier: 512, 1K, 2K, 4K")
    parser.add_argument("--aspect-ratio", help="Aspect ratio: 1:1, 16:9, 9:16, etc.")
    parser.add_argument("--n", type=int, default=1, help="Number of images (1-10, default: 1)")
    parser.add_argument("--output", help="Output file path (overriding auto-naming)")
    parser.add_argument("--quality", choices=["auto", "low", "medium", "high"], help="Quality level")
    parser.add_argument("--output-format", choices=["png", "jpeg", "webp"], default="png", help="Output format")
    parser.add_argument("--output-dir", default=DEFAULT_CACHE_DIR, help="Output directory")

    args = parser.parse_args()

    output_dir = args.output_dir
    if args.output:
        output_dir = os.path.dirname(os.path.abspath(args.output))

    paths = generate_image(
        prompt=args.prompt,
        model=args.model,
        resolution=args.resolution,
        aspect_ratio=args.aspect_ratio,
        n=args.n,
        quality=args.quality,
        output_format=args.output_format,
        output_dir=output_dir,
    )

    if args.output and len(paths) == 1:
        os.rename(paths[0], args.output)
        paths[0] = args.output

    for p in paths:
        print(p)


if __name__ == "__main__":
    main()
