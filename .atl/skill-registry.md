# Agent Teams Lite - Skill Registry

This file maps technical skills and SDD phases to their physical paths on disk so the Orchestrator can inject them into sub-agents.

## Core Agent Team (SDD Workflows)

| Skill | Path | Description |
|-------|------|-------------|
| sdd-init | `/home/pedroj/.config/opencode/skills/sdd-init/SKILL.md` | Initialize Spec-Driven Development context |
| sdd-explore | `/home/pedroj/.config/opencode/skills/sdd-explore/SKILL.md` | Investigate codebase and explore ideas |
| sdd-propose | `/home/pedroj/.config/opencode/skills/sdd-propose/SKILL.md` | Create change proposals |
| sdd-spec | `/home/pedroj/.config/opencode/skills/sdd-spec/SKILL.md` | Write specifications with requirements |
| sdd-design | `/home/pedroj/.config/opencode/skills/sdd-design/SKILL.md` | Create technical designs |
| sdd-tasks | `/home/pedroj/.config/opencode/skills/sdd-tasks/SKILL.md` | Break down changes into tasks |
| sdd-apply | `/home/pedroj/.config/opencode/skills/sdd-apply/SKILL.md` | Implement changes from tasks |
| sdd-verify | `/home/pedroj/.config/opencode/skills/sdd-verify/SKILL.md` | Validate implementation |
| sdd-archive | `/home/pedroj/.config/opencode/skills/sdd-archive/SKILL.md` | Archive completed changes |

## GitHub Workflow Skills

| Skill | Path | Trigger |
|-------|------|---------|
| issue-creation | `/home/pedroj/.config/opencode/skills/issue-creation/SKILL.md` | Creating GitHub issues, bug reports, feature requests |
| branch-pr | `/home/pedroj/.config/opencode/skills/branch-pr/SKILL.md` | Creating pull requests, opening PRs |

## Engineering Skills

| Skill | Path | Trigger |
|-------|------|---------|
| skill-creator | `/home/pedroj/.config/opencode/skills/skill-creator/SKILL.md` | Creating new AI agent skills |
| go-testing | `/home/pedroj/.config/opencode/skills/go-testing/SKILL.md` | Writing Go tests, Bubbletea TUI testing |
| judgment-day | `/home/pedroj/.config/opencode/skills/judgment-day/SKILL.md` | Parallel adversarial review |

## Project-Local Skills (Ortiz-specific)

| Skill | Path | Trigger |
|-------|------|---------|
| ortiz-db-sync | `/home/pedroj/Desktop/ortiz-consignataria/.agents/skills/ortiz-db-sync/SKILL.md` | Sync Railway DB to local, "traer base de producción" |

## Project Context

**Project**: ortiz-consignataria
**Stack**: Python/Flask, SQLite, TailwindCSS, Docker
**Architecture**: Monorepo organizado (web_app, data_pipeline, shared_code)
**Persistence**: engram

## Code Context Patterns

Use these patterns to auto-load skills based on file types:

| File Pattern | Relevant Skills |
|--------------|-----------------|
| `*.py` | sdd-apply (Flask patterns) |
| `test_*.py` | sdd-verify (pytest patterns) |
| `requirements*.txt` | sdd-apply (Python deps) |
| `Dockerfile` | sdd-apply (Docker patterns) |
| `*.html`, `*.css` | sdd-apply (Tailwind patterns) |

## Auto-Injection Rules

When launching sub-agents, the orchestrator MUST:
1. Match file extensions being modified to skills above
2. Include matching skill compact rules in the prompt
3. Pass the skill content inline, NOT as file paths
