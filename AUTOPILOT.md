# Autopilot Mission — Soundcloud2MP3 (FlyKrewDownloader)

**Mission:** This app needs a full rebuild. Work toward it steadily: modernize the
codebase, fix reliability issues, and improve the download/convert experience.
"Valuable" = anything that moves the rebuild forward or makes the current tool more
reliable for Drew's real use. Cosmetic churn is not valuable.

**Mode:** suggest-first — propose ONE task per run; Drew approves with "carry on".
**Cadence:** weekly.

**Boundaries:**
- Never break the currently-working download flow without a tested replacement.
- No new paid services/dependencies without Drew's approval.
- Note: Drew's old local experiments are saved in a git stash ("Drew's local edits
  saved 2026-07-07") — consult them if relevant, don't blindly restore them.

## Drew's Wishlist
*(Items here always outrank the agent's own ideas. Add from any device: "add to the Soundcloud2MP3 wishlist: ...")*
- (empty — brain-dump welcome)

## Run Log
2026-07-07 | Autopilot installed (pilot project) | —
2026-07-07 | SUGGESTED: Keep the download engine fresh at runtime | The engine that actually grabs the audio (yt-dlp) is baked into the app when it's built and never changes after that. SoundCloud and YouTube tweak their sites every few weeks, and when they do, a frozen engine quietly stops working — friends who downloaded the app months ago suddenly get "download failed" with no fix except Drew rebuilding and re-releasing. Proposed task: on startup, quietly check for and load the latest engine into a writable folder, always falling back to the built-in one if offline or if the update looks broken (so the working download flow can never break). Rough size: one focused, well-tested change to how the app loads its engine. This is the single biggest reliability win for real-world use.
