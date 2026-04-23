---
name: writing-skills
description: Use when creating new skills, editing existing skills, or verifying skills work before deployment
---

## Overview
**Writing skills IS Test-Driven Development applied to process documentation.**

You write test cases (pressure scenarios with subagents), watch them fail (baseline behavior), write the skill (documentation), watch tests pass (agents comply), and refactor (close loopholes).

**Core principle:** If you didn't watch an agent fail without the skill, you don't know if the skill teaches the right thing.

**REQUIRED BACKGROUND:** You MUST understand superpowers:test-driven-development before using this skill.

**Official guidance:** See anthropic-best-practices.md for Anthropic's official skill authoring best practices.

## What is a Skill?
A **skill** is a reference guide for proven techniques, patterns, or tools.

**Skills are:** Reusable techniques, patterns, tools, reference guides
**Skills are NOT:** Narratives about how you solved a problem once

### Types
- **Technique** — Concrete method with steps (condition-based-waiting, root-cause-tracing)
- **Pattern** — Way of thinking about problems (flatten-with-flags, test-invariants)
- **Reference** — API docs, syntax guides, tool documentation

## When to Create a Skill
**Create when:** technique wasn't obvious, you'd reference it again, pattern applies broadly, others would benefit.

**Don't create for:** one-off solutions, well-documented standard practices, project-specific conventions (use CLAUDE.md), mechanical constraints (automate with regex/validation instead).

## Directory Structure

```
skills/
  skill-name/
    SKILL.md              # Main reference (required)
    supporting-file.*     # Only if needed
```

**Flat namespace** - all skills in one searchable namespace.
**Separate files for:** heavy reference (100+ lines), reusable tools/scripts.
**Keep inline:** principles, concepts, code patterns (< 50 lines).

## SKILL.md Structure
**Frontmatter (YAML):**
- Two required fields: `name` and `description` (max 1024 chars total)
- `name`: Letters, numbers, hyphens only
- `description`: Third-person, "Use when..." format, describes ONLY triggering conditions (NOT what it does)
- Keep under 500 characters if possible

```markdown
---
name: Skill-Name-With-Hyphens
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
Core principle in 1-2 sentences.

## When to Use
Bullet list with SYMPTOMS and use cases. When NOT to use.

## Core Pattern
Before/after code comparison.

## Quick Reference
Table or bullets for scanning.

## Implementation
Inline code or link to file for heavy reference.

## Common Mistakes
What goes wrong + fixes.
```

## The Iron Law
```
NO SKILL WITHOUT A FAILING TEST FIRST
```
This applies to NEW skills AND EDITS. Write skill before testing? Delete it. Start over. No exceptions.

> **Detailed testing methodology:** See `references/testing-guide.md` for the complete TDD cycle for skills, all skill type testing approaches, rationalization tables, and bulletproofing techniques.

## CSO (Claude Search Optimization)
**Critical:** Future Claude needs to FIND your skill. Description = When to Use, NOT What the Skill Does.

> **Comprehensive CSO guide:** See `references/cso-guide.md` for description writing rules, keyword coverage, naming conventions, token efficiency techniques, and cross-referencing patterns.

## Flowcharts & Code Examples
Use flowcharts ONLY for non-obvious decision points. One excellent code example beats many mediocre ones.

> **Detailed guidance:** See `references/flowchart-and-examples.md` for flowchart rules, graphviz conventions, code example best practices, and directory layout examples.

## STOP: Before Moving to Next Skill
**After writing ANY skill, you MUST STOP and complete the deployment process.**

Do NOT create multiple skills in batch without testing each. Deploying untested skills = deploying untested code.

## Skill Creation Checklist (TDD Adapted)

**RED Phase - Write Failing Test:**
- [ ] Create pressure scenarios (3+ combined pressures for discipline skills)
- [ ] Run scenarios WITHOUT skill - document baseline behavior verbatim
- [ ] Identify patterns in rationalizations/failures

**GREEN Phase - Write Minimal Skill:**
- [ ] Name uses only letters, numbers, hyphens
- [ ] YAML frontmatter with `name` and `description` (max 1024 chars)
- [ ] Description starts with "Use when..." with specific triggers/symptoms
- [ ] Keywords throughout for search (errors, symptoms, tools)
- [ ] Address specific baseline failures identified in RED
- [ ] One excellent example (not multi-language)
- [ ] Run scenarios WITH skill - verify agents now comply

**REFACTOR Phase - Close Loopholes:**
- [ ] Identify NEW rationalizations from testing
- [ ] Add explicit counters (if discipline skill)
- [ ] Re-test until bulletproof

**Quality Checks:**
- [ ] Small flowchart only if decision non-obvious
- [ ] Quick reference table
- [ ] Common mistakes section
- [ ] No narrative storytelling

## Discovery Workflow
How future Claude finds your skill:
1. **Encounters problem** → 2. **Finds SKILL** (description matches) → 3. **Scans overview** → 4. **Reads patterns** → 5. **Loads example** (only when implementing)

**Optimize for this flow** - put searchable terms early and often.

## The Bottom Line
**Creating skills IS TDD for process documentation.**
Same Iron Law. Same cycle: RED → GREEN → REFACTOR. Same benefits.
