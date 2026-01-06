# Contributing

Thank you for your interest in contributing to DeepTutor! That means a lot for our team! 🎉

You can join our [Discord community](https://discord.gg/aka9p9EW) for further discussion.

## Ways to Contribute

- 🐛 **Report bugs** — Open an issue with reproduction steps
- 💡 **Suggest features** — Share your ideas in discussions
- 📖 **Improve docs** — Fix typos, add examples
- 🔧 **Submit PRs** — Code contributions welcome!

## 🔄 Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature`
2. **Make changes**: Follow existing code style and conventions
3. **Test locally**: Ensure your changes work correctly
4. **Run pre-commit**: `pre-commit run --all-files` ⚠️ **Required before PR!**
5. **Commit**: Pre-commit hooks will auto-format your code
6. **Push & PR**: Open a pull request with a clear description

## Development Setup

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/DeepTutor.git
cd DeepTutor
```

### 2. Set Up Environment

```bash
# Using conda (recommended)
conda create -n aitutor python=3.10
conda activate aitutor

# Or using venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
# Automated installation (recommended)
bash scripts/install_all.sh

# Or manual installation
pip install -r requirements.txt
npm install
```

### 4. Install Pre-commit Hooks

```bash
# Install pre-commit
pip install pre-commit

# Install Git hooks
pre-commit install

# (Optional) Run checks on all files
pre-commit run --all-files
```

> After installing Git hooks, they will run **automatically** on every commit — no need to remember!

## 🛠️ Code Quality Tools

We use automated tools to maintain code quality:

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **Ruff** | Python linting & formatting | `pyproject.toml` |
| **Prettier** | Frontend code formatting | `web/.prettierrc.json` |
| **detect-secrets** | Security check | `.secrets.baseline` |

::: warning IMPORTANT
**Before submitting a PR, you MUST run:** `pre-commit run --all-files`

CI will automatically check this and **reject PRs** that fail pre-commit checks.
:::

Every time you run `git commit`, pre-commit hooks will automatically:
- Format Python code with Ruff
- Format frontend code with Prettier
- Check for syntax errors
- Validate YAML/JSON files
- Detect potential security issues

> **Note**: The project uses **Ruff format** instead of Black to avoid formatting conflicts.

## Common Commands

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
- `feat`: for a new feature (MINOR version bump)
- `fix`: for a bug fix (PATCH version bump)
- `docs`: for documentation-only changes
- `style`: for formatting changes (whitespace, semicolons)
- `refactor`: for code changes that neither fix a bug nor add a feature
- `test`: for adding or correcting tests
- `chore`: for routine tasks (build processes, dependencies)

## Reporting Issues

- Use GitHub Issues to report bugs or suggest features
- Provide detailed information about the issue
- Include steps to reproduce if it's a bug

## Code of Conduct

Please be respectful and inclusive. We're building a welcoming community for learners and contributors alike.

## Questions?

- Open a [GitHub Discussion](https://github.com/HKUDS/DeepTutor/discussions)
- Join our [Discord Community](https://discord.gg/aka9p9EW)
- Check existing issues for similar questions

---

### Let's build a tutoring system for the whole community TOGETHER! 🚀
