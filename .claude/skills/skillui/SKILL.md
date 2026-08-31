---
name: skillui
description: Reverse-engineer the design system (colors, fonts, spacing, components, animations, scroll journeys) of any live URL, repository, or local folder using the skillui CLI, packaged as a .skill file Claude Code picks up automatically. Use when the user wants to clone, match, or extract the visual design of an existing site or codebase, or bootstrap a new UI that looks like a reference.
---

# SkillUI

`skillui` (npm) is a pure static-analysis CLI — no AI, no API keys, no cloud calls. It crawls a URL, repo, or folder, extracts every design token (colors, fonts, spacing, components, animations) plus scroll screenshots, and packages the result as a `.skill` folder containing a `CLAUDE.md` with everything inlined.

## Usage

```bash
npx skillui <url-or-path> [output-dir]
```

Open the generated output folder (or point Claude Code at it) and the extracted design system loads automatically via its `CLAUDE.md` — use it as the reference when generating matching UI.

## When to use

- The user wants a new page/component/app to visually match an existing site or codebase.
- The user asks to "reverse-engineer", "extract", or "clone the look of" a design system, brand palette, spacing scale, or component library.

Homepage: https://skillui.vercel.app/
