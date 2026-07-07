---
name: ship
description: Ship current work — typecheck/build, commit, push, merge to main, verify the live Vercel deployment answers. Use whenever Drew says "ship", "merge", "push", "deploy", or "send it".
---

# Ship

Drew's repos auto-deploy: GitHub push → Vercel production. Run this checklist in
order. Stop and report at the first failure — never continue past a red step.

1. Run the project's typecheck and build (check the project's own scripts). Both must pass.
2. Commit all changes with a descriptive message.
3. Push the branch.
4. Merge to main (or follow the project's PR convention).
5. Wait for the auto-deploy, then verify the production URL returns HTTP 200 and
   spot-check that the changed page actually renders.
6. Report the live URL. Never claim "deployed" without step 5 passing.

Never instruct Drew to set env vars or configure the deploy before code is
committed and merged.
