---
name: web-storyscroll-practices
description: Apply when building, scaffolding, or structuring a website, web app, or front-end JS library/component for the user. Brings the conventions the user asked to standardize on, modeled on the StoryScroll repo (github.com/xxlh/StoryScroll) — a scroll-driven canvas storytelling library. Covers three things: (1) the scroll+canvas storytelling interaction pattern (chapters/sprites triggered by scroll position), (2) project/build structure (src/lib/examples split, multi-format bundle output), and (3) documentation/demo conventions (parameter tables, standalone example pages). Use this whenever the user says "build a web/site/page" without further spec, as the default baseline to follow unless they ask for something else (a specific framework, a different stack, a quick prototype).
---

# Web project conventions (StoryScroll baseline)

The user asked to default to these conventions, drawn from `xxlh/StoryScroll`, whenever building a web project. Apply what's relevant to the request's scope — a full library needs all three; a single page mainly needs the interaction pattern and demo conventions.

## 1. Scroll + canvas storytelling interaction pattern

When the ask involves scroll-driven narrative, animated sections, or canvas-based visuals:

- Model content as **chapters containing sprites**, not one flat timeline. A chapter is a container with its own local coordinate space; sprites inside it move together.
- Animations are **position-triggered**, not time-triggered: a sprite/chapter declares a target state, a distance over which to animate (`section`), and a scroll position that triggers it (`triggerPosition`). Reaching that scroll position scrubs the animation proportionally to scroll distance — not a fixed-duration tween.
- Keep a **separate path for discrete (non-scroll-scrubbed) animations** — effects that should play once a trigger position is reached, independent of further scrolling (e.g. a fade-in via `act`/`action` with a tween library), rather than overloading the scroll-scrubbed path for everything.
- Support **progressive/incremental asset loading** (don't block first render on every asset) and a **debug mode** that prints the current scroll position — both pay off immediately once there's more than a couple of sections.
- Default canvas setup to a **fixed design width** with the renderer handling scaling, so coordinates in code stay simple integers instead of viewport-relative math everywhere.

## 2. Project / build structure

For anything beyond a single static page:

- Split `src/` (source), `lib/` (built output), `examples/` (standalone demo pages) — don't mix source and build artifacts in one folder.
- Build with a bundler producing **multiple output formats from one source** when the thing is consumable as a library: CommonJS (`main`), ES module (`module`), and a minified UMD bundle (`umd` + `umd:name` in `package.json`) for plain `<script>` tag usage.
- Treat optional/plugin functionality (e.g. an animation-action add-on, a projection add-on) as **separate entry points** compiled to their own small bundles, not bundled into the core file — so a consumer who doesn't need the extra only pays for the core.
- Add a build banner (name/version/author/license/year) to generated bundle files.
- `.npmignore` excludes `src/`, `examples/`, editor config — ship only `lib/` (+ README/LICENSE/package.json) to npm consumers; `.gitignore` only excludes `node_modules/` and editor config, since the repo itself needs `src/`/`examples/` checked in.
- Log something human-readable during the build (what's compiling, output size after gzip) rather than a silent build.

## 3. Documentation and demo conventions

- README structure: short description → visual examples (GIFs/links to live demos) → install (npm, then a CDN `<script src>` snippet for no-build usage) → usage code sample → **a parameter table per API surface** (name, type, default) → browser support matrix → license → credits.
- Every documented method gets its parameters listed immediately under the code sample that introduces it — don't push all parameter docs to one appendix.
- `examples/` holds **one minimal, self-contained HTML file per feature/demo** (not one giant kitchen-sink demo) — each pulls in only the built `lib/` files it needs via `<script>` tags plus a few lines of inline init code, so it's readable top-to-bottom without jumping files.
- Serve examples with the simplest possible static server (a few lines of Express serving `examples/` and `lib/`) rather than a dev-server toolchain, since the demos are plain HTML/JS with no build step of their own.
