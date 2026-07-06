# WatchLess Codex Instructions

## Instruction Priority

- Treat sections that say `must`, `do not`, or `ask before` as hard rules.
- Treat the remaining guidance as defaults to follow unless the user explicitly overrides them.
- If two rules conflict, prefer:
  1. explicit user request
  2. safety and data-preservation rules
  3. narrow, low-waste execution

## Owner Context

- The project owner is non-technical.
- Explain commands, files, errors, frameworks, and build steps in plain language.
- Do not assume the owner understands terminal usage, packaging, local servers, or test tooling.
- Keep explanations concise, but include enough context for clear decision-making.

## Clarification Rule

- Before generating substantial output, proposals, or code changes, briefly confirm your understanding of what the user is asking.
- If key context is missing, unclear, or ambiguous, stop and ask targeted follow-up questions before committing to an answer or implementation.
- Optimize for highest-quality output with the fewest revision rounds.
- Do not make the user repeat “any questions before we commit”; treat that as the default expectation in this repo.
- For trivial, low-risk requests where the intent is fully clear, keep the confirmation brief and proceed.

## Default Behavior

- Treat each request as a targeted patch unless broad investigation, architecture work, refactoring, or cleanup is explicitly requested.
- Reuse existing context and recent findings.
- Treat follow-up messages as deltas to the current task.
- Do not restart analysis from scratch unless something materially changed.
- Confirm understanding early enough that the user can correct direction before substantial work begins.
- Inspect the minimum necessary files first.
- Do not scan unrelated folders.
- Do not run broad searches unless needed to find the exact affected code.
- Expand scope only when evidence shows it is necessary.

## Project Structure

- `watchless_app/templates/index.html`: app shell and main layout
- `watchless_app/static/css/styles.css`: visual styling
- `watchless_app/static/js/app.js`: main frontend behavior
- `watchless_app/static/js/modules/`: focused frontend helpers
- `watchless_app/services/`: backend logic
- `tests/test_storage_and_api.py`: focused automated coverage
- `desktop_app.py`: desktop launcher from source
- `run-dev.sh`: preferred local run shortcuts
- `publish.sh`: packaged app build script

## Editing Rules

- Make the smallest correct change.
- Follow existing WatchLess patterns.
- Avoid unrelated refactors.
- Avoid formatting-only edits.
- Avoid renaming files, functions, or user-facing concepts unless required.
- Do not add dependencies unless explicitly approved.
- Do not change configs unless the task requires it.
- Do not delete files unless explicitly approved.
- Preserve existing user changes and work safely in a dirty git tree.

## Validation

- Prefer these local commands:
  - Browser preview: `./run-dev.sh browser`
  - Source desktop app: `./run-dev.sh app`
  - Packaged app rebuild: `./run-dev.sh build`
- Run only the narrowest relevant test, preview, typecheck, lint, or build command.
- Default backend validation: `.venv/bin/python -m pytest tests/test_storage_and_api.py`
- Use browser preview for most UI, copy, spacing, and formatting changes.
- Use source desktop app preview when the change affects desktop-window behavior or the app should be checked in its real desktop shell.
- Use packaged rebuild only when the user asks for it, packaging/distribution behavior changed, or a packaged-app-specific check is necessary.
- Do not rebuild the packaged app unless the user asks, packaging is affected, or a packaged-app check is necessary.
- If a tool is missing, explain the missing tool and use the next best narrow validation when possible.

## Packaging Rules

- Source code changes appear in browser preview and source desktop runs immediately after restart.
- `dist/WatchLess.app` is a packaged snapshot and does not update until rebuilt.
- Do not assume the packaged app reflects recent code edits unless `./run-dev.sh build` was run.
- Ask before doing full packaged rebuilds when a lighter preview path is enough.
- If the user reports “the app did not change,” first verify whether they opened the source run or an old packaged build before changing code again.

## Approval Gates

- Ask before doing any of the following:
  - Full repo analysis
  - Full builds
  - Full test-suite runs
  - Dependency installs
  - Major refactors
  - Broad bug-fixing passes
  - Publishing, releasing, pushing, or deploying
  - Destructive git or file operations
  - Changes to signing, notarization, credentials, or production-style config

## Product And UI Work

- Preserve the current WatchLess design direction unless the user asks for a redesign.
- Prioritize readable summaries, clear controls, and efficient use of screen space.
- Prefer practical app UI over marketing-style layouts.
- Keep the main reading area clean and legible.
- Verify that important text and controls do not overlap or overflow on common viewport sizes.
- Do not weaken Markdown rendering or summary formatting behavior without explicit approval.

## UI Acceptance Checks

- For summary rendering changes, verify that headings, lists, spacing, and emphasis still render correctly.
- For layout changes, verify that the main reading area remains usable and that controls stay reachable.
- For sidebar or panel changes, verify both expanded and collapsed states.
- For copy or instruction changes, keep language short and understandable for a non-technical user.
- Before considering UI work done, check the lightest realistic preview path that matches the change.

## Documentation

- Keep user-facing docs free of internal implementation noise unless developer-facing detail is requested.
- Write instructions for a non-technical owner.
- Prefer short, repeatable workflows over long explanations.

## Output Style

- Be concise.
- Report only:
  1. What changed
  2. Files touched
  3. Validation performed or recommended
  4. Risks or assumptions
- Do not paste large files unless asked.
- Do not give long reasoning traces.
- End with one most relevant next action.
