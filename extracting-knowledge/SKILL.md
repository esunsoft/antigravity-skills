---
name: extracting-knowledge
description: Use when completing a task that involved non-obvious debugging, trial-and-error discovery, misleading error messages, or project-specific workarounds - evaluates whether reusable knowledge should be preserved as a new Skill or Knowledge Item
---

# Extracting Knowledge

## Overview

**Core principle:** Valuable discoveries should outlive the session that produced them.

After completing a task, evaluate whether the work produced knowledge worth preserving. Not every task produces extractable knowledge — be selective.

## Quick Evaluation (< 30 seconds)

Ask yourself these 3 questions after completing a task:

1. **Was discovery involved?** Did I investigate, experiment, or debug to find the solution?
2. **Is it reusable?** Would this help someone (including future-me) facing a similar problem?
3. **Is it non-obvious?** Would the solution NOT be found by simply reading official docs?

**All 3 YES → Extract.** Any NO → Skip. Move on.

## Quality Gates

Before extracting, verify ALL criteria:

| Gate | Question |
|------|----------|
| **Reusable** | Will this help with future tasks, not just this one? |
| **Non-trivial** | Did this require actual discovery, not just doc lookup? |
| **Specific** | Can I describe exact trigger conditions and solution? |
| **Verified** | Has this solution actually worked, not just theoretically? |

Fail any gate → don't extract.

## Deduplication Check

Before creating new knowledge, search existing skills and KIs:

| Found | Action |
|-------|--------|
| Nothing related | Create new |
| Same trigger, same fix | Update existing (bump version) |
| Same trigger, different root cause | Create new + add cross-references both ways |
| Partial overlap | Add variant subsection to existing |
| Same domain, different problem | Create new + add `See also:` links |
| Stale or wrong existing | Mark deprecated, add replacement |

## Output Decision

```
Is this knowledge...
├── Project-specific pattern or config? → Knowledge Item (KI)
├── Broad technique reusable across projects? → Skill (use writing-skills)
└── Specific error + fix combo? → Knowledge Item (KI)
```

**REQUIRED:** If creating a Skill, follow `writing-skills` for the full TDD creation process.

## Knowledge Structure

When creating a KI or updating an existing one, use this structure:

```markdown
## Problem
[What happened, what was the symptom]

## Trigger Conditions
[Exact error messages, observable symptoms, environment]

## Root Cause
[What actually caused the problem — often different from the symptom]

## Solution
[Step-by-step fix, with code/commands if applicable]

## Verification
[How to confirm the fix worked]

## Notes
[Caveats, edge cases, when NOT to apply this]
```

## Anti-Patterns

| ❌ Don't | ✅ Do Instead |
|----------|-------------|
| Extract every task | Only extract genuine discoveries |
| Write vague descriptions | Include exact error messages and triggers |
| Extract unverified guesses | Only extract what actually worked |
| Duplicate official docs | Link to docs + add what's missing |
| Create without checking existing | Always run dedup check first |

## Self-Reflection Prompts

Use after significant tasks:

- "What did I just learn that wasn't obvious before starting?"
- "If I faced this exact problem again in 6 months, what would I wish I knew?"
- "What error message led me here, and what was the actual cause?"
- "Would I tell a colleague about this trick?"
