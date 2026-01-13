# Contributing to DeepTutor

Thank you for your interest in contributing to DeepTutor! We are trying to make DeepTutor smooth and robust, for every developers to develop and conribute.

Join our community for discussion and support:

<p align="center">
  <a href="https://discord.gg/zpP9cssj"><img src="https://img.shields.io/badge/Discord-Join_Community-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>&nbsp;
    <a href="https://github.com/HKUDS/DeepTutor/issues/78"><img src="https://img.shields.io/badge/WeChat-Join_Group-07C160?style=for-the-badge&logo=wechat&logoColor=white" alt="WeChat"></a>&nbsp;
  <a href="./Communication.md"><img src="https://img.shields.io/badge/Feishu-Join_Group-00D4AA?style=for-the-badge&logo=feishu&logoColor=white" alt="Feishu"></a>
</p>

## ⚠️ Contribution Requirements

> [!IMPORTANT]
> **All contributions must be based on the `dev` branch!**
>
> 1. Fork the repository and clone it locally
> 2. **Always pull from the `dev` branch**: `git checkout dev && git pull origin dev`
> 3. Create your feature branch from `dev`: `git checkout -b feature/your-feature`
> 4. Submit your PR to the `dev` branch (NOT `main`)
> 5. Ensure all pre-commit checks pass before submitting

## 🛠️ Code Quality

We use automated tools to maintain code quality:

- **Ruff** — Python linting & formatting (`pyproject.toml`)
- **Prettier** — Frontend formatting (`web/.prettierrc.json`)
- **detect-secrets** — Security scanning

> [!IMPORTANT]
> **Before submitting a PR, you MUST run:** `pre-commit run --all-files`
>
> CI will automatically check this and **reject PRs** that fail pre-commit checks.

<details>
<summary><b>Setting Up Pre-commit (First Time Only)</b></summary>

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

</details>

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

### 💡 How to Get Started

1. Check our [Issues](https://github.com/HKUDS/DeepTutor/issues) for tasks labeled `good first issue` or `help wanted`
2. Comment on the issue you'd like to work on
3. Follow the contribution process above
4. Join our [Discord](https://discord.gg/aka9p9EW) if you have questions!

---

### Let's build DeepTutor TOGETHER! 🚀
