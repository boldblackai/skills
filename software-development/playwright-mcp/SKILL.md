---
name: playwright-mcp
description: "Install, configure, and use the Playwright MCP server for browser automation in Hermes — navigation, screenshots, form filling, accessibility snapshots, and DOM interaction via headless Chromium."
version: 1.0.0
author: BoldBlack
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [playwright, browser, automation, mcp, screenshots, chromium]
---

# Playwright MCP Browser Automation

Use for general browser automation: navigating pages, taking screenshots (proofs, QA, before/after), filling forms, clicking elements, reading accessibility snapshots, and extracting text/DOM state via headless Chromium.

For **performance-specific** work (FCP/LCP, cold-cache measurement, frame polling), use the `web-performance` skill instead — it has specialized CDP measurement patterns.

## Install (one-time, per container restart)

The Playwright MCP browser binary must live in `~/.hermes/ms-playwright/` (persists across restarts). The default location `~/.cache/ms-playwright/` is wiped on container restart.

```bash
PLAYWRIGHT_BROWSERS_PATH=~/.hermes/ms-playwright npx playwright install chromium
```

Find the installed binary path:
```bash
ls ~/.hermes/ms-playwright/chromium-*/chrome-linux/chrome
```

## Configure the MCP server in Hermes

The default browser channel is `"chrome"` which requires root. Override with `--executable-path` to use Chromium for Testing (no root needed).

**Important:** Do NOT use `hermes config set` for this — it corrupts list-typed values (the `args` array becomes a flat JSON string). Instead remove and re-add:

```bash
hermes mcp remove playwright
hermes mcp add playwright \
  --command npx \
  --args '["-y", "@playwright/mcp@latest", "--headless", "--executable-path", "<path-to-chromium-binary>"]'
```

Replace `<path-to-chromium-binary>` with the absolute path from the install step above (e.g. `/home/harness/.hermes/ms-playwright/chromium-1187/chrome-linux/chrome`).

After reconfiguring, restart the gateway for the new MCP args to take effect.

## Common workflows

### Navigate and snapshot
```
mcp__playwright__browser_navigate(url="https://example.com")
mcp__playwright__browser_snapshot()  # accessibility tree — better than screenshot for interaction
```

The accessibility snapshot is preferred over screenshots when you need to **act** on the page — it returns a tree of interactive elements with refs you can click/type into. Use `browser_take_screenshot` when you need a visual (proofs, QA, layout verification).

### Take a screenshot
```
mcp__playwright__browser_take_screenshot(type="png", scale="css")
```
Options: `type` = png/jpeg, `scale` = css (smaller, consistent) or device (high-res), `fullPage=true` for full scrollable page, `element`/`target` for element-scoped shots.

### Fill a form
```
mcp__playwright__browser_fill_form(fields=[
  {"target": "<ref>", "name": "email", "type": "textbox", "value": "a@b.com"},
  {"target": "<ref>", "name": "plan", "type": "combobox", "value": "Pro"}
])
```
Get the `<ref>` values from `browser_snapshot`. Field types: textbox, checkbox, radio, combobox, slider.

### Click an element
```
mcp__playwright__browser_click(target="<ref>", element="Submit button")
```

### Find text on the page
```
mcp__playwright__browser_find(text="Sign up")  # case-insensitive substring
mcp__playwright__browser_find(regex="/error.*/i")
```
Returns matching snapshot nodes with surrounding context — cheaper than a full snapshot when locating an element.

### Run JavaScript on the page
```
mcp__playwright__browser_evaluate(function="() => document.title")
```
For reading computed styles, extracting text, or checking DOM state.

### Wait for content
```
mcp__playwright__browser_wait_for(text="Dashboard loaded")
mcp__playwright__browser_wait_for(textGone="Loading spinner")
mcp__playwright__browser_wait_for(time=2)  # seconds
```

## Pitfalls

- **Viewport silently collapses between navigations — verify width before every full-page screenshot.** Observed: `browser_resize(1280x900)` sticks for the first shot, but after later `browser_navigate` calls the viewport reset to narrow widths (602/490/433/390px). Full-page screenshots then capture a crushed mobile-responsive layout (single-column grid, tall skinny PNG) that *looks* like a rendering bug but is a viewport bug. Fix: run `browser_evaluate(() => { window.resizeTo(1280, 900); return document.documentElement.clientWidth; })` immediately before **every** screenshot and assert the returned width; also verify saved PNG dimensions (`struct.unpack('>II', data[16:24])` on the IHDR) match expectations after a shoot batch.

- **Binary location** — must be `~/.hermes/ms-playwright/`, not `~/.cache/ms-playwright/`. The cache dir is wiped on restart.
- **`hermes config set` corrupts args lists** — use `hermes mcp remove` + `hermes mcp add` instead. `hermes config set` only writes scalars; dicts/lists become flat JSON strings.
- **Default channel needs root** — always pass `--executable-path` pointing at the Chromium for Testing binary, or override the channel.
- **`page.evaluateOnNewDocument` doesn't exist in Playwright MCP** — use CDP `Page.addScriptToEvaluateOnNewDocument` via `browser_run_code_unsafe` if you need to inject before navigation.
- **Snapshots vs screenshots** — snapshots return interactive element refs you can act on; screenshots are visual-only. For QA/proof-of-work, capture screenshots. For automation, navigate via snapshot refs.
- **Caching hides first-load bugs** — default Playwright hits cache. If diagnosing first-load issues, disable cache via CDP `Network.setCacheDisabled` (see `web-performance` skill).
