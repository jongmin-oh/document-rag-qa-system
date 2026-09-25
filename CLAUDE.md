# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, report it and remove it in a separate, clearly described change (see §5).

When your changes create orphans:
- Remove imports/variables/functions/files that YOUR changes made unused, in the same change.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. No Dead Code, No Legacy (project rule)

**The repository contains only code that the current pipeline runs. This rule overrides §3 where they conflict.**

- Every file, function, and branch must be reachable from a documented entry point
  (`python -m app.ingest.build`, `python -m app.tools.pdf_to_markdown.export`, `pytest tests`, or a later documented command).
- When an approach is replaced, delete the old implementation in the same change. Do not keep it "just in case".
  Git history is the archive.
- Forbidden: commented-out code, `_old`/`_v2`/`legacy`/`deprecated` files or functions, unused parameters or config flags,
  compatibility shims, fallback paths for removed behavior, and TODOs without an owner and a reason.
- Moving or renaming a module updates every import, path, and doc reference in the same change. No re-export aliases.
- Generated files (`app/data/processed/`) must be regenerated whenever their generator changes; never leave outputs
  from a previous version.
- Docs (`README.md`, `decision/*.md`) describe only the current design. A replaced decision is recorded as
  "what changed and why" in the relevant section, not kept as a parallel description.

Before finishing any change, verify:
```
1. pyflakes app tests                      → no unused imports/variables
2. grep for old module/file names           → no stale references
3. python -m app.ingest.build && pytest tests → outputs regenerated, tests pass
```

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.
