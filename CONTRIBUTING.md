# Contributing to DeepTutor

Thank you for your interest in contributing to DeepTutor! That means a lot for our team!

You can join our discord community for further discussion: https://discord.gg/aka9p9EW

## 🔄 Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Follow existing code style and conventions
3. **Test locally**: Ensure your changes work correctly
4. **Run pre-commit**: `pre-commit run --all-files` ⚠️ **Required before PR!**
5. **Commit**: Pre-commit hooks will auto-format your code
6. **Push & PR**: Open a pull request with a clear description

## 🛠️ Code Quality

We use automated tools to maintain code quality:

- **Ruff** — Python linting & formatting (`pyproject.toml`)
- **Prettier** — Frontend formatting (`web/.prettierrc.json`)
- **detect-secrets** — Security scanning

> [!IMPORTANT]
> **Before submitting a PR, you MUST run:** `pre-commit run --all-files`
>
> CI will automatically check this and **reject PRs** that fail pre-commit checks.

### Setting Up Pre-commit (First Time Only)

**Step 1: Install pre-commit**
```bash
# Using pip
pip install pre-commit

# Or using conda
conda install -c conda-forge pre-commit
```

**Step 2: Install Git hooks (recommended)**
```bash
cd DeepTutor
pre-commit install
```
> After this, hooks will run **automatically** on every commit — no need to remember!

**Step 3: Run checks on all files**
```bash
pre-commit run --all-files
```

### Common Commands

```bash
# Normal commit (hooks run automatically if installed)
git commit -m "Your commit message"

# Manually check all files (do this before pushing!)
pre-commit run --all-files

# Update hooks to latest versions
pre-commit autoupdate

# Skip hooks (not recommended, only for emergencies)
git commit --no-verify -m "Emergency fix"
```

## 📋 Commit Message Format

```
<type>: <short description>

[optional body]

[optional footer(s)]
```
**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
- `feat: for a new feature. This typically corresponds to a MINOR version bump in Semantic Versioning.`
- `fix: for a bug fix. This typically corresponds to a PATCH version bump.`
- `chore: for routine tasks that do not modify source code or tests (e.g., updating build processes).`
- `docs: for documentation-only changes.`
- `style: for changes that do not affect the meaning of the code (e.g., whitespace, semicolons).`
- `refactor: for code changes that neither fix a bug nor add a feature.`
- `test: for adding missing tests or correcting existing tests.`
---

### Let's build a tutoring system for the whole community TOGETHER! 🚀
