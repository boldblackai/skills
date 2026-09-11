---
name: image-gen
description: "Generate and edit images via OpenRouter's unified Image API using any image model (gpt-5-image, gemini-3-pro-image, flux, etc.) — text-to-image, image-to-image editing, chroma-key background transparency, and battle-tested brand/logo iteration workflows. Requires OPENROUTER_IMAGE_API_KEY."
version: 1.0.0
author: BoldBlack
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [image, generation, openrouter, dall-e, flux, gemini, logo, branding]
required_environment_variables:
  - name: OPENROUTER_IMAGE_API_KEY
    prompt: OpenRouter Image API key
    help: Get a key from https://openrouter.ai/keys
---

# Image Generation via OpenRouter

Generate images from text prompts using OpenRouter's unified Image API (`/api/v1/images`).

## Requirements

- `OPENROUTER_IMAGE_API_KEY` must be set in `~/.hermes/.env` (passed to scripts via regular env passthrough)

## How to Use

Run the `scripts/generate.py` script from the skill directory. The agent should execute it via terminal:

```bash
python3 ~/.hermes/skills/creative/image-gen/scripts/generate.py "your prompt here"
```

### Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `prompt` | Yes | Text description of the desired image |
| `--model` | No | Model slug (default: `openai/gpt-5-image-mini`) |
| `--resolution` | No | Resolution tier: `512`, `1K`, `2K`, `4K` (default: auto) |
| `--aspect-ratio` | No | e.g. `1:1`, `16:9`, `9:16` (default: auto) |
| `--n` | No | Number of images (1-10, default: 1) |
| `--output` | No | Output file path (default: `~/.hermes/image_cache/<timestamp>.png`) |
| `--output-dir` | No | Directory for outputs (default: `~/.hermes/image_cache/`) |
| `--quality` | No | `auto`, `low`, `medium`, `high` (default: auto) |
| `--output-format` | No | `png`, `jpeg`, `webp` (default: png) |

### Example

```bash
# Basic generation
python3 ~/.hermes/skills/creative/image-gen/scripts/generate.py "a cyberpunk cat in neon rain"

# With options
python3 ~/.hermes/skills/creative/image-gen/scripts/generate.py "a cyberpunk cat" --model google/gemini-2.5-flash-image --resolution 2K --aspect-ratio 16:9

# Multiple images
python3 ~/.hermes/skills/creative/image-gen/scripts/generate.py "variety of cats" --n 3
```

### Output

- Prints the saved file path(s) to stdout
- The agent should respond with `MEDIA:<path>` for each image so the platform delivers it natively

## Popular Models

| Model | Notes | Cost/img |
|-------|-------|----------|
| `openai/gpt-5-image-mini` | Default. Fast, good quality | ~$0.009 |
| `google/gemini-2.5-flash-image` | Free tier available | free tier |
| `google/gemini-3-pro-image` | High quality, strong prompt adherence, good for logos/icons | ~$0.13 |
| `black-forest-labs/flux.2-pro` | High quality | ~$0.04 |
| `bytedance-seed/seedream-4.5` | Balanced | varies |
| `openai/gpt-image-1` | OpenAI's dedicated image model | varies |

**Cost/quality tiers** (rough): budget (`gpt-5-image-mini`, ~$0.009) → mid (`flux.2-pro`, ~$0.04) → premium (`gemini-3-pro-image`, ~$0.13). For brand/logo/icon work where the user will iterate, default to a mid or premium model — the budget model often needs many more rounds to converge.

## Pitfalls

- If OPENROUTER_IMAGE_API_KEY is not set, the script will fail with a clear error
- Some models don't support `n > 1` — check model capabilities if needed
- Image generation can take 10-30s depending on model and resolution
- Response is base64-encoded and decoded to a file locally

## Image editing (image+text → image)

`generate.py` only does text→image. For editing an existing image — adding text to a logo, restyling, extending the canvas, creating variations — use `scripts/edit.py`, which calls the chat completions endpoint with the input image attached.

```bash
python3 ~/.hermes/skills/creative/image-gen/scripts/edit.py <input_image> "<edit prompt>" --output <path> [--model MODEL] [--aspect-ratio 16:9] [--image-size 2K]
```

### Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `input` | Yes | Path to the source image |
| `prompt` | Yes | Edit instruction |
| `--output` | Yes | Output file path |
| `--model` | No | Model slug (default: `google/gemini-3-pro-image`) |
| `--aspect-ratio` | No | Output AR via `image_config`: `1:1`, `16:9`, `9:16`, `2:3`, `3:2`, `4:3`, `4:5`, `5:4`, `21:9` |
| `--image-size` | No | Output resolution: `0.5K`, `1K`, `2K`, `4K` |

### Example

```bash
# Turn a square logo into a 16:9 banner with wordmark
python3 ~/.hermes/skills/creative/image-gen/scripts/edit.py ./logo.png \
  "Keep the icon on the LEFT unchanged. Extend the dark background right and add the wordmark 'example.dev' in terminal-green monospace, vertically centered." \
  --model google/gemini-3-pro-image \
  --aspect-ratio 16:9 --image-size 2K \
  --output ./banner.png
```

### Implementation notes (for debugging only — the script already handles these)

- Payload must include `"modalities": ["text", "image"]` — without it, models return text only.
- Generated images come back in a **top-level `message.images` array**, NOT in `message.content`. Per OpenRouter docs (https://openrouter.ai/docs/features/multimodal/image-generation). Shape: `{"choices":[{"message":{"role":"assistant","content":"...","images":[{"type":"image_url","image_url":{"url":"data:image/png;base64,..."}}]}}]}`. If you ever see `content: null` and think "all models broken," you're reading the wrong field — check `message.images`.
- Use `image_config: {"aspect_ratio": "...", "image_size": "..."}` to control output dimensions.

## Background transparency (chroma keying) — when the model can't do alpha

Image models (including gemini-3-pro-image, gpt-5-image, flux) do **not** output a true alpha channel — they generate RGB on a solid background. When the user asks for a "transparent background" or a PNG with transparency, do NOT retry with a different model or prompt the model harder ("output transparent PNG") — it won't work. Instead, generate (or edit) on a **solid known background color**, then key it out programmatically with Pillow.

### Two approaches — prefer magenta chromakey

#### Approach A: Magenta chromakey (RECOMMENDED)

Generate (or image→image edit) the subject on a **solid pure magenta (#FF00FF)** background, then key by chroma: background = R>200, G<40, B>200. This is robust against slight background noise/dithering (the model rarely produces a perfectly uniform magenta — there are 40-80 unique colors in a "solid" corner patch — but chroma separation cleanly distinguishes magenta from any non-magenta subject).

**Text→image variant** (when regenerating from prompt):
```
"...The background MUST be a SOLID FLAT PURE MAGENTA (#FF00FF) chromakey background —
uniform flat color, no gradient, no texture, no dots, no pattern, just solid magenta
everywhere behind the subject."
```

**Image→image variant** (PREFERRED when you have an approved design — preserves the subject):
```
edit.py approved_design.png "Keep the EXACT same [subject], colors, composition, and
every detail unchanged. ONLY change the background: replace it with a SOLID FLAT PURE
MAGENTA (#FF00FF) background — uniform flat magenta everywhere behind the subject,
no gradient, no texture. The subject itself must remain identical."
```

The image→image variant is strongly preferred for brand work — it preserves the exact approved subject and only swaps the background. Text→image regeneration produces a *different* subject (same prompt, different seed), which defeats the purpose of having an approved version.

**Keying:** `scripts/make_transparent.py` with `--mode magenta` (default).

#### Approach B: Luminance keying (for existing dark-background images)

When you already have an image on a dark background and can't regenerate, key by luminance. Sample the background color from corners, set pixels at background luminance → alpha 0, well above → alpha 255, with a feather band between.

**Caveat:** If the subject contains dark areas close to the background luminance (e.g. a dark grey book on a dark charcoal background), luminance keying will eat into the subject — the subject's shadows become transparent holes. Luminance also catches background dithering/noise as "not background," leaving scattered semi-transparent specks. For dark subjects on dark backgrounds, always use Approach A (regenerate on magenta) instead.

### Keying script

`scripts/make_transparent.py` — takes an input PNG, keys the background, and outputs an RGBA PNG:

```bash
# Magenta background (recommended)
python3 ~/.hermes/skills/creative/image-gen/scripts/make_transparent.py input.png --output output.png

# Dark background (luminance mode — sample corners for bg color)
python3 ~/.hermes/skills/creative/image-gen/scripts/make_transparent.py input.png --output output.png --mode luminance

# Also resize to 64x64
python3 ~/.hermes/skills/creative/image-gen/scripts/make_transparent.py input.png --output output.png --resize 64
```

### Verification

After keying, verify programmatically — **do NOT trust a vision model** to confirm transparency. Vision models render transparent pixels as white/solid and will report "background is white, not transparent." Check the alpha channel histogram instead:

```python
from PIL import Image
a = Image.open('output.png').split()[3]
hist = a.histogram()
print(f'transparent: {hist[0]}, opaque: {hist[255]}, partial: {sum(hist[1:255])}')
```

A good magenta key: ~77% transparent, ~23% opaque, ~250 partial-alpha (feathered edges). If partial-alpha is 0, edges will be jagged — the feather band is too narrow.

### Pillow installation

Pillow is often NOT importable system-wide on hardened hosts (PEP 668 + no write to system dist-packages). Spin up a throwaway venv:

```bash
cd /tmp && uv venv -q imgvenv && uv pip install --python /tmp/imgvenv/bin/python Pillow -q
/tmp/imgvenv/bin/python ~/.hermes/skills/creative/image-gen/scripts/make_transparent.py input.png --output output.png
```

### When NOT to use this

- If the subject contains magenta/pink/hot-pink elements, magenta chromakey will eat them — use a different chroma color (green-screen green, pure blue) instead.
- If the background is not uniform (gradients, textures, multiple colors), simple keying won't work — you need a matting model (rembg, background removal API), which is outside this skill's scope.

## Debugging repeated failures — "all models can't be broken"

If two or more independent models / providers return the same shape of failure (e.g. all return `content: null`, all 4xx identically, all silently produce nothing), **stop retrying models and check the OpenRouter docs for your endpoint.** The probability that N independent backend providers broke the same way at the same time is near zero; the bug is almost certainly in your request shape or your response parser.

Concrete instance from a real session: an image-edit script called `/chat/completions` with `modalities:["text","image"]` and an input image. Gemini-3-pro-image, OpenAI gpt-5-image, and Gemini-3.1-flash-image all returned `message.content: null` with reasoning text. Three retries, ~$0.50 burned, before the user said *"all of these models can't be having the same issue"* and pointed at the docs. Root cause: the extractor was reading `message.content`; OpenRouter actually returns generated images in a **top-level `message.images` array** (documented at https://openrouter.ai/docs/features/multimodal/image-generation). The images had been present in every response. The `edit.py` script now reads `message.images` correctly.

Rule: on the SECOND identical-shape failure across models, fetch the docs BEFORE the third attempt. Don't burn a third retry on the same unexamined request. Root-cause investigation precedes fix attempts — chasing symptoms by swapping models is the wrong reflex.

## When an image edit fails — DO NOT fall back to ImageMagick/compositing

If the model's image-edit endpoint is not returning image bytes (e.g. you get reasoning text but `message.content` is null), **abort and report the blocker to the user.** Do NOT pivot to ImageMagick / PIL / ffmpeg / manual compositing to "salvage" the result. Reasons:
- The user asked for the model to do the work; a hand-composited substitute is a different deliverable.
- Image models mangle exact text rendering, so a "fix it in post" composite silently degrades quality on the exact axis the user cares about.
- Hunting for which imaging lib is installed burns turns; report and let the user decide.

Correct response on edit-endpoint failure: state plainly that the model is not returning image bytes, show the raw response shape, stop.
- **HTTP 402 "Insufficient credits"** means the OpenRouter account is out of credits for that model — retry with a cheaper model, or retry the same model later (credits may have been topped up). Do NOT treat it as a permanent tool failure.
- **Glyph distortion**: image models routinely mangle specific characters/symbols in logos (`///`, `./`, `$$`, etc.). When the image must contain exact glyphs, explicitly state in the prompt: *"must read clearly as the typographic characters X"* and name the characters. Budget models distort more; premium models (`gemini-3-pro-image`, `flux.2-pro`) adhere better.

## Brand / logo / icon workflow

Users iterate aggressively on brand and icon work — expect 5-10 refinement rounds. The loop is:

1. Generate.
2. User critiques **specific elements** ("slashes look wrong", "scanlines too faint", "too 3D").
3. Regenerate with only the targeted changes. Do NOT over-explain or re-pitch options between rounds — the user wants the next image, not commentary.

### Parallel concept exploration (cut multiple directions at once)

When the user is early in a brand/logo/icon session and undecided on direction, do NOT generate one concept and wait. Offer 3–4 distinct concepts as a `clarify` choice; if the user says "do all of them" (or implies it), fire all N generations in parallel (separate `terminal` calls in one turn), each sharing the locked house style but varying the subject/concept. Deliver all results together so the user picks a direction visually rather than imagining it from prose. This collapses 3–4 sequential round-trips into one.

Only do this at the concept-exploration stage — once a direction is chosen, revert to single-generation targeted iteration.

### "Too specific/realistic" — swap the subject, don't just dial down realism

When the user says a subject is "too specific" or "too realistic/literal" (e.g. a shipping container reading like a photo of a shipping container), the fix is NOT to push "15% less photoreal" harder on the same subject — a literal object stays literal even in illustration style. The fix is to **swap for a more symbolic/abstract subject that carries the same meaning**. Re-pitch the swap as a `clarify` choice, then cut the new concept.

### Image→image edit to preserve a good attribute while changing another

When a specific version has an attribute *exactly right* (a color tone, a texture, a composition detail) and the user wants a different attribute changed, **edit that version with image→image** rather than text-regenerating from scratch. Text-regen will not reproduce the exact good attribute — you'll lose the thing the user liked. The edit keeps the good attribute as the visual baseline and applies only the requested change.

Concrete instance: v2.4 of a logo had a muted racing-red the user loved, but 2 of 5 straps were charcoal. v2.5 tried to reproduce "all red" via text→image and got a brighter, wrong red. v2.7a/b were cut by editing v2.4 directly ("make all straps red" / "make all straps black") — the good muted-red tone was preserved because the edit worked from v2.4's pixels. The VERSIONS.md lineage recorded the branch parent explicitly (v2.7a/b branched from v2.4, not v2.6).

This is also the correct tool when the user names the input image explicitly ("image→image where 2.4 is the input"). Honor the named source file — don't substitute a different input.

Style-axis vocabulary that maps cleanly to prompts (pick one per axis, don't hedge):

- **Finish**: `flat vector` / `semi-realistic but clean` / `glossy 3D` / `macOS-style app icon`
- **Depth**: `no gradients, no 3D` (flat) vs `soft drop shadow, subtle depth` (icon)
- **Detail**: `minimalist` vs `detailed`

Always pin **exact hex colors** for brand work — don't let the model pick greens/blues.

### Effect-intensity calibration (the "subtle" trap)

When the user asks for a "subtle" effect ("subtle glow", "make it pop just a bit", "slightly more depth"), image models will routinely over-deliver — you ask for a faint glow and get a full embossed metallic chromatic bevel. Defense: in the prompt, **explicitly enumerate the forbidden heavy-effect vocabulary**, not just the desired effect. Example that worked:

> *"very subtle effect… a faint soft glow/halo, or a very slight letterpress — NOT 3D, NOT embossed, NOT metallic, NOT beveled, NOT chromatic. Subtle = barely noticeable, just enough that it feels intentional."*

The negation list matters more than the positive description. Treat "subtle" / "a bit" / "slightly" as signals to add a NOT-list, every time. The user will tell you "way too much effect" if you skip this — and that correction costs a generation cycle.

### Branching on over-correction

When a version over-shoots what the user asked for (e.g. they said "subtle" and you delivered "embossed"), do NOT iterate on the over-shot version to dial it back. **Branch from the version BEFORE the over-shot one.** Reason: iterating on a heavily-effected image leaves residual effect artifacts even after you ask for "less"; starting from the cleaner prior version gives a truer subtle result.

Versioning convention: if `v3` over-shot and `v2` was the last good state, the correction is `v3.1` branched from `v2` (input image = `v2-*.png`), NOT `v3.1` branched from `v3`. Record the branch parent explicitly in VERSIONS.md so the lineage is traceable.

### Versioning during iteration (OPT-IN — only when user requests)

Versioning generations into a project dir is **not the default**. Most one-off image gens should just land in the cache root as timestamped files. Only set up versioning when the user explicitly signals lock-in/revert intent, e.g. "lock this in", "save this version", "go back to what we had", "can we keep a version around", or when they're clearly deep in a multi-round brand/logo/icon session and referencing prior versions by number.

When triggered:

1. Make a project dir: `~/.hermes/image_cache/<project>/` (e.g. `my-logo/`). If the user has already been generating into the cache root, retroactively copy the approved/mentioned generations in as `v1-<suffix>`, `v2-<suffix>`, etc.
2. Copy each NEW generation in as `v<n>-<short-descriptive-suffix>.<ext>` (e.g. `v1-amazing-semirealistic.png`, `v3-talons-at-tear-bottoms.png`). Use **minor versions** (`v3.1-...`) for tweaks that branch off a prior version.
3. Maintain a `VERSIONS.md` in that dir: per version, the **full prompt** (so it's reproducible), the file link, and a one-line **status** (`✅ approved base`, `variation explored`, `V3 variant, X changed`). Update it in the same turn you generate.
4. Respond with `MEDIA:<versioned-path>` so the user sees the specific version, not a raw timestamp.
5. Honor "revert to vN" / "throw away vX" by pointing back at (or regenerating from) that saved version's file/prompt, and update VERSIONS.md accordingly — deletions prune both the file and the VERSIONS.md entry.
6. If the user branches a **new artifact type** off an approved version (e.g. "make a banner from the v3.1 logo"), create a sibling project dir (e.g. `my_logo_text/`) with its own VERSIONS.md, and reference the source version by relative path.

Do NOT version casual/throwaway generations. The mechanism exists for brand work where the user cares about being able to roll back.

### Small-icon / favicon deliverables (16/32/64px)

When the final artifact is a favicon or app icon (16/32/64px), image models can't emit at icon dimensions directly — generate at 1K (square) then downscale with PIL. `Image.LANCZOS` on an RGBA-converted source gives the cleanest result.

Pillow is often NOT importable system-wide on hardened hosts (PEP 668 + no write to system dist-packages). Don't fight `uv pip install --system` — spin up a throwaway venv in `/tmp`:

```bash
cd /tmp && uv venv -q imgvenv && uv pip install --python /tmp/imgvenv/bin/python Pillow -q
/tmp/imgvenv/bin/python -c "from PIL import Image; Image.open('src.png').convert('RGBA').resize((64,64), Image.LANCZOS).save('out-64.png')"
```

**Design pitfall — detail collapses at 64px.** Fine elements that read well at 1K vanish or merge at icon size: a small pushpin becomes a red dot, thin strokes disappear, a tiny accent square fuses with its neighbor. When the target is ≤64px, design *bolder and simpler* than the 1K version — fewer elements, thicker shapes, higher contrast. If a detail that dies at 64px (e.g. a pushpin) is the whole point, regenerate it larger/more angular so it survives the downscale, rather than shipping a version where it reads as an ambiguous blob. Deliver both the 1K source and the downsized icon so the user can judge the source and iterate from it.

### PNG optimization (reducing file size before delivery/upload)

After generating and processing transparent PNGs, optimize them before uploading or delivering. Two tools, both via `mise` (the preferred tool installer on hardened hosts — do NOT use apt-get or manual binary downloads for CLI tools; use `mise install <tool>@latest && mise use -g <tool>@latest && eval "$(mise activate bash)"`):

**oxipng** (lossless PNG optimization — run this first):

```bash
mise install oxipng@latest && mise use -g oxipng@latest && eval "$(mise activate bash)"
oxipng -o max --strip safe --alpha input.png
```

Typical savings: 2-17% depending on image complexity. For RGBA images with many unique colors (2K+), lossless PNG optimization has diminishing returns — the image is already near-optimal. Don't spend more than one oxipng pass.

**WebP lossless** (much smaller, supports alpha — use when the target platform supports WebP):

```python
from PIL import Image
Image.open('input.png').convert('RGBA').save('output.webp', 'WebP', lossless=True, quality=100, method=6)
```

Typical savings: 12-68% vs the original PNG. WebP lossless is especially effective on larger images (1K source: 68% smaller). However, some platforms/CDNs may not serve `.webp` natively — check before committing.

**When to optimize:** always run oxipng on PNGs before upload. If the file is still large and the platform supports WebP, also produce a `.webp` version. The tools are fast — don't overthink it.

### User-provided reference images in edits

When the user drops a reference image to steer an image→image edit, copy it into the project dir as `reference-vN-<source>.<ext>` before the edit so the lineage is traceable and the user can refer back to the exact input. Pass that path to `edit.py`. Do not pass the image by ephemeral cache path alone — it may be garbage-collected, and naming it in the project dir keeps the edit's input pinned.

### Model locking during brand/logo iteration

Once the user settles on a model for a brand/logo project, treat it as **locked for the whole project** — do not suggest or silently switch to other models on later iterations, even if a generation fails. Aesthetic consistency across versions depends on staying on one model; mixing models mid-project produces visibly inconsistent lineage that ruins the "can we revert to vN" property the versioning is there to provide.

Signals that a lock is in effect (any one):
- The user names a specific model when kicking off iteration ("lets use X").
- The user corrects a model choice ("switch back to X", "stay with X", "only use X"). Repeated/restated corrections mean a previous response drifted — treat the escalation as a strong signal and stop offering alternates.

When locked:
1. Record it at the TOP of the project's `VERSIONS.md` header, not just per-version: e.g. `Model: \`google/gemini-3-pro-image\` ONLY (locked — no other models for this project)`.
2. Keep every subsequent generation on that model. If a generation fails, retry the SAME model (adjust prompt, resolution, or aspect ratio) rather than swapping models — swapping is the wrong reflex here and the user will push back.
3. If you believe a different model is genuinely warranted (e.g. locked model is returning errors across many retries), say so explicitly and ask — do not switch unilaterally.

This lock is project-scoped, not global: a different logo project can use a different model. The lock lives in that project's VERSIONS.md so it carries across sessions without the user re-stating it.
