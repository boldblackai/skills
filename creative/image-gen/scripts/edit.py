#!/usr/bin/env python3
"""Image editing via OpenRouter chat completions (image+text → image).

Sends an existing image to a multimodal model along with an edit prompt.
Use this for: adding text to a logo, restyling, extending canvas, inpainting,
variations on an existing image, etc.

Usage:
    python3 edit.py <input_image> "<edit prompt>" --output <path> [--model MODEL] [--aspect-ratio 16:9] [--image-size 2K]

Key facts (per https://openrouter.ai/docs/features/multimodal/image-generation):
  - Must set `modalities: ["text", "image"]` or models return text only.
  - Generated images come back in `message.images[]` (NOT `message.content`).
  - Use `image_config` for aspect_ratio / image_size on the output.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.request
import urllib.error

API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "google/gemini-3-pro-image"


def _load_api_key() -> str:
    """Load OPENROUTER_IMAGE_API_KEY from the environment."""
    key = os.environ.get("OPENROUTER_IMAGE_API_KEY", "")
    if key:
        return key
    print("ERROR: OPENROUTER_IMAGE_API_KEY not found in environment. Add it to ~/.hermes/.env.", file=sys.stderr)
    sys.exit(1)


def guess_mime(path: str) -> str:
    ext = path.lower().rsplit(".", 1)[-1]
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "gif": "image/gif"}.get(ext, "image/png")


def edit_image(input_path: str, prompt: str, model: str,
               aspect_ratio: str | None = None, image_size: str | None = None) -> dict:
    api_key = _load_api_key()
    with open(input_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    mime = guess_mime(input_path)
    data_url = f"data:{mime};base64,{b64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "modalities": ["text", "image"],
    }
    image_config: dict = {}
    if aspect_ratio:
        image_config["aspect_ratio"] = aspect_ratio
    if image_size:
        image_config["image_size"] = image_size
    if image_config:
        payload["image_config"] = image_config

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
    print(f"Editing with {model}...", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection error: {e.reason}", file=sys.stderr)
        sys.exit(1)


def extract_image(resp: dict) -> tuple[bytes, str] | None:
    """Pull an image out of the response.

    OpenRouter returns generated images in `message.images` as a list of
    {type: "image_url", image_url: {url: "data:image/png;base64,..."}} parts.
    This is the documented, primary location — NOT message.content.
    Ref: https://openrouter.ai/docs/features/multimodal/image-generation
    """
    choices = resp.get("choices", [])
    if not choices:
        return None
    msg = choices[0].get("message", {})

    # PRIMARY: top-level message.images (per OpenRouter docs)
    for img_part in msg.get("images", []) or []:
        if not isinstance(img_part, dict):
            continue
        iu = img_part.get("image_url") or {}
        url = iu.get("url") if isinstance(iu, dict) else None
        if url and url.startswith("data:"):
            header, b64 = url.split(",", 1)
            mime = "image/png"
            m = re.match(r"data:([^;]+)", header)
            if m:
                mime = m.group(1)
            try:
                return base64.b64decode(b64), mime
            except Exception:
                pass

    # FALLBACK: image embedded in message.content (some providers)
    content = msg.get("content")
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") in ("image", "image_url"):
                img = part.get("image_url") or part.get("image") or {}
                url = img.get("url") if isinstance(img, dict) else None
                if url and url.startswith("data:"):
                    header, b64 = url.split(",", 1)
                    mime = "image/png"
                    m = re.match(r"data:([^;]+)", header)
                    if m:
                        mime = m.group(1)
                    return base64.b64decode(b64), mime

    # FALLBACK: content is a string with a markdown image URL
    if isinstance(content, str):
        m = re.search(r"!\[[^\]]*\]\((https?://[^)]+)\)", content)
        if m:
            url = m.group(1)
            print(f"Fetching returned image URL: {url}", file=sys.stderr)
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read(), r.headers.get("Content-Type", "image/png")

    return None


def main():
    ap = argparse.ArgumentParser(description="Edit an image via OpenRouter chat completions")
    ap.add_argument("input", help="Path to input image")
    ap.add_argument("prompt", help="Edit prompt")
    ap.add_argument("--model", default=DEFAULT_MODEL, help=f"Model slug (default: {DEFAULT_MODEL})")
    ap.add_argument("--aspect-ratio", help="e.g. 16:9, 1:1, 2:3 (image_config)")
    ap.add_argument("--image-size", help="1K, 2K, 4K (image_config)")
    ap.add_argument("--output", required=True, help="Output path")
    args = ap.parse_args()

    resp = edit_image(args.input, args.prompt, args.model,
                      aspect_ratio=args.aspect_ratio, image_size=args.image_size)
    usage = resp.get("usage", {})
    cost = usage.get("cost")
    if cost is not None:
        print(f"Cost: ${cost:.4f}", file=sys.stderr)

    result = extract_image(resp)
    if not result:
        print("ERROR: No image found in response.", file=sys.stderr)
        print(json.dumps(resp, indent=2)[:2000], file=sys.stderr)
        sys.exit(1)

    img_bytes, mime = result
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "wb") as f:
        f.write(img_bytes)
    print(args.output)


if __name__ == "__main__":
    main()
