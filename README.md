# portfolio-weightage-eval

![Python](https://img.shields.io/badge/python-3.11+-blue)

## Overview

`portfolio-weightage-eval` evaluates an investment portfolio's sector weightage on a monthly
cadence to detect concentration risk. It supports holdings across three markets — US
(NYSE/NASDAQ), UK (LSE), and Singapore (SGX) — and normalises all values to SGD before
calculation. Sector data is sourced via yFinance with a four-layer SGX fallback chain; results
are stored as JSON snapshots and uploaded to Supabase for historical tracking and month-over-month
shift analysis.

---

## Prerequisites

- **Python ≥ 3.11**
- **uv** — fast Python package and project manager
  ([installation guide](https://docs.astral.sh/uv/getting-started/installation/))

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/<your-org>/portfolio-weightage-eval.git
cd portfolio-weightage-eval
```

### 2. Install dependencies

```bash
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, creates a `.venv` in the project root, and
installs all pinned dependencies. The `.venv` directory is gitignored and never committed —
every developer creates it locally from the lockfile.

### 3. Install git hooks

```bash
uv run pre-commit install
```

This registers the hooks defined in `.pre-commit-config.yaml` into `.git/hooks` so they run
automatically on every `git commit`.

### 4. Configure environment variables

The repository includes `.env.example`, a template that lists every required variable with
placeholder values. Copy it to `.env` and fill in your own credentials:

```bash
cp .env.example .env   # then edit .env with real values
```

`.env` is listed in `.gitignore` — secrets never leave your local machine. `.env.example` is
committed to the repository because it contains **no secrets**; it documents which variables the
project requires so developers know exactly what to configure.

---

## Pre-commit Hooks

Hooks run automatically on `git commit`. To run them manually against all files:

```bash
uv run pre-commit run --all-files
```

| Hook | What it checks |
|---|---|
| `trailing-whitespace` | Removes trailing spaces from all lines |
| `end-of-file-fixer` | Ensures every file ends with exactly one newline |
| `mixed-line-ending` | Normalises all line endings to LF |
| `check-merge-conflict` | Blocks commits that contain conflict markers (`<<<<<<<`) |
| `check-added-large-files` | Blocks files larger than 500 KB from being committed |
| `check-yaml` | Validates YAML file syntax |
| `check-toml` | Validates TOML file syntax |
| `check-json` | Validates JSON file syntax |
| `detect-private-key` | Blocks accidental commits of private keys or secrets |
| `ruff` (lint) | Enforces PEP 8, bugbear, and pyupgrade rules; auto-fixes where possible |
| `ruff-format` | Enforces consistent formatting (double quotes, 100-character lines) |

> **Note:** If `ruff` or `ruff-format` auto-fix files, the commit is blocked. Re-stage the
> modified files (`git add .`) and re-commit.

---

## Environment Variables

All secrets and runtime configuration are supplied via environment variables. See `.env.example`
for a ready-to-copy template.

| Variable | Purpose |
|---|---|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase service-role or anon key |
| `BROKERAGE_API_KEY` | API key for the chosen brokerage integration |
| `BASE_CURRENCY` | Currency all values are normalised to before calculation (default: `SGD`) |
| `SKEW_THRESHOLD` | Fallback sector weight (%) threshold for the "any single sector" rule (default: `40`) |
| `OUTPUT_DIR` | Local directory for JSON snapshot files |
| `OUTPUT_EXCEL` | Set to `true` to generate the optional multi-tab Excel report (default: `false`) |

> **Scaffold note:** `SUPABASE_URL`, `SUPABASE_KEY`, and `BROKERAGE_API_KEY` are not yet used
> at this stage (PR 1 of 7). They must be present and correctly set before running the full
> pipeline from PR 5 onward.

---

## Project Status

This repository is currently at **PR 1 — Project Scaffold** (milestone 1 of 7). The full
roadmap, domain rules, and planned pull requests are documented in
[CLAUDE.md](./CLAUDE.md).
