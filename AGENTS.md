# Agent Guidelines & Repository Rules

## Git Commit Policy
- **Commit when appropriate:** Create clean, atomic git commits upon completing a logical phase, task, bugfix, or significant milestone.
- **Conventional Commits:** Use standard conventional commit format:
  - `feat:` for new capabilities or domain additions
  - `fix:` for bug fixes
  - `refactor:` for code refactoring or reorganization without behavior changes
  - `test:` for adding or updating tests
  - `docs:` for documentation updates
  - `chore:` for settings, dependency, or configuration maintenance
- **Descriptive Messages:** Provide meaningful commit messages summarizing the rationale and impact of the change.
- **Pre-commit Inspection:** Always verify `git status` and `git diff` before committing to prevent accidental commits of environment files (`.env`), cache files (`__pycache__`), or unwanted temporary artifacts.

## Engineering Workflow
- **Phase-by-Phase Discipline:** Complete only the explicitly assigned phase. Do not skip phases or jump directly to premature implementation.
- **Root Cause Resolution:** When debugging, reproduce first with regression tests, identify root cause, and implement minimal targeted fixes.
- **Tech Stack Guardrails:**
  - Python 3.12 runtime compatibility.
  - Django 4.2 LTS & DRF 3.15.2 best practices.
  - PostgreSQL 16 as authoritative database (SQLite is strictly a local dev fallback).
  - Business Brain boundary: Deterministic business systems establish facts and metrics; AI advisory never silently creates authoritative records without approval.
