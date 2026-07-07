

# ── Portable Agent Kit (local + cloud parity) — installed 2026-07-07 ──
Skills for this repo live in `.claude/skills/` and load on demand — same roster as
Drew's local machine, so cloud sessions behave identically to local ones.

## Communication (always on)
Drew is a non-technical founder (vibe coder). Describe what he sees on screen and what
happens when he interacts — never variable names, function names, file paths, or code
snippets in chat, unless he explicitly asks to see code. Prefer the simplest solution;
touch only what the task requires.

## Skill Routing (deterministic — never wait to be asked)
- Any UI or UX work (pages, components, layout, styling, redesigns): invoke the `impeccable` skill BEFORE writing frontend code.
- Any bug, test failure, or unexpected behavior: invoke `systematic-debugging` before proposing fixes.
- Before claiming anything is done, fixed, or deployed: invoke `verification-before-completion`.
- Scan the skills menu each session and use whatever matches the task without being asked.

## Merge / Push / Deploy Guardrails
Drew's repos generally auto-deploy: GitHub push → Vercel production. Whenever Drew says
"merge", "push", "deploy", or "ship" — or you are about to do any of those — run this
in order, stopping at the first failure:
1. Typecheck and build pass (use the project's own scripts).
2. Everything committed with a descriptive message.
3. Branch pushed, then merged to main.
4. Confirm the live production URL returns 200 (not 404) and the changed page actually loads.
5. Only then report success, with the live URL. Never ask Drew to set env vars or deploy
   before code is committed and merged.

## Scope & Safety Defaults
- Build the simplest version that satisfies the request; confirm scope in one sentence before building anything elaborate.
- Marketing/consent checkboxes always default to UNCHECKED (opt-in).
- Never run production database changes from ideas phrased as questions — only explicit directives.
- Never generate icons/images via headless-browser rendering; ask Drew for finished assets.
