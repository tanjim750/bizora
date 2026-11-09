# Agent team: what works in Antigravity

Checked on 2026-11-09 against the official Antigravity documentation (`antigravity.google/docs`: rules, skills, workflows, workflows-to-skills, custom subagents, permissions, goal, boost, teamwork, browser, sandbox).
The owner's machine has the **Antigravity IDE** (desktop entry "Antigravity IDE"; `~/.gemini/config` exists). Several features are documented only for the Antigravity **App** and **CLI**; where the docs do not mention the IDE this page says "not stated". Test those once (the checklist is in `README.md`).

## What each surface supports (from the docs)
| Feature | IDE | App | CLI | Notes |
|---|---|---|---|---|
| Rules (`.agents/rules/*.md`, `AGENTS.md`, `GEMINI.md`) | yes | yes | yes | Files need frontmatter with `trigger`, 24,000 bytes each, 20,000 tokens total for always-on rules; only the workspace root is scanned (not `frontend/AGENTS.md`) |
| Skills (`.agents/skills/<name>/SKILL.md`) | yes | yes | yes | The agent loads them by description; `/<skill-name>` slash command is documented for App and CLI |
| Workflows (`.agents/workflows/*.md`) | yes (deprecated) | migrated to skills | | Still work; a skill with the same name wins; 12,000 characters each |
| Several agent conversations in parallel | yes | yes | yes | Shared or separate workspace copies: not stated for the IDE |
| Custom subagents (`.agents/agents/*.md`) | **not stated** | yes | yes | Parent calls them with `invoke_subagent`; they start with a clean context; can run concurrently; nesting depth 10 |
| `/goal` (autonomous, no iteration cap) | not stated | yes | yes | Ends only when the agent proves completion or you stop it; approvals still apply |
| `/boost`, `/teamwork` | not stated | paid plans | paid plans | `/teamwork` works in its own directory (`~/teamwork_projects`), so it is not used here |
| `/browser` subagent | yes | yes | | Drives **your Google Chrome** (version 144 or later, remote debugging on). Chrome is not installed here |
| Reads Claude Code folders (`.claude/agents`, `.claude/skills`, `CLAUDE.md`) | not stated | not stated | not stated | Not relied on; everything was ported |

## Our agents and how they map
| Claude kit role | In Antigravity | File |
|---|---|---|
| `system-architect` (orchestrator) | Skill and workflow `/system-architect` run by the main agent (not a custom agent: a wrong `tools` list can hang a custom agent, and the main agent needs all tools) | `.agents/skills/system-architect`, `.agents/workflows/system-architect.md` |
| `design-reviewer` | Read-only custom subagent, plus skill `/design-review` as the fallback | `.agents/agents/design-reviewer.md` |
| `code-reviewer` | Read-only custom subagent, plus skill `/code-review` | `.agents/agents/code-reviewer.md` |
| `security-reviewer` | Read-only custom subagent, plus skill `/security-review` | `.agents/agents/security-reviewer.md` |
| `architect-reviewer` | Read-only custom subagent, plus skill `/architect-review` | `.agents/agents/architect-reviewer.md` |
| Builders | The main agent only. No builder subagents (shared working tree, merge risk) | |

The reviewer subagents use only the tool names that appear in the official example (`view_file`, `grep_search`, `run_command`). If one hangs or the IDE does not list them, use the matching skill instead: the content is the same.

## How the team is used (every phase end)
1. The main agent finishes the phase, runs `/verify`, commits.
2. It invokes the four reviewers in parallel with a self-contained brief: phase, commit range, pages touched, path of the verification report and screenshots (`~/bizora-shots/<label>/report.json`).
3. Each returns a findings table and `VERDICT: SHIP | FIX FIRST | BLOCK`. The main agent fixes every critical, high and medium finding, re-verifies, records the verdicts in `PROGRESS.md`.
If subagents are unavailable the main agent runs the four review skills itself, or starts a new conversation per reviewer in the side panel and pastes the same brief.

## If you want a more independent second opinion in the morning
Open a **new** conversation in Antigravity and say: "Review the branch frontend-overhaul against main with the design-review and code-review skills; do not edit files." Or bring the branch back to Claude here.
