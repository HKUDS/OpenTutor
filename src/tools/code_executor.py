#!/usr/bin/env python
"""
Run Code Tool - Code execution tool
Execute Python code in isolated workspace, preserving original input/output structure.
"""

import ast
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

RUN_CODE_WORKSPACE_ENV = "RUN_CODE_WORKSPACE"
RUN_CODE_ALLOWED_ROOTS_ENV = "RUN_CODE_ALLOWED_ROOTS"
DEFAULT_WORKSPACE_NAME = "run_code_workspace"
PROJECT_ROOT = Path(__file__).resolve().parents[2]

from src.logging import get_logger

logger = get_logger("CodeExecutor")


def _load_config() -> dict[str, Any]:
    """Load run_code configuration from main.yaml and module configs"""
    try:
        from src.services.config import load_config_with_main

        # Try loading from solve_config (most common use case)
        try:
            config = load_config_with_main("solve_config.yaml", PROJECT_ROOT)
            run_code_config = config.get("tools", {}).get("run_code", {})
            if run_code_config:
                logger.debug("Loaded run_code config from solve_config.yaml (with main.yaml)")
                return run_code_config
        except Exception as e:
            logger.debug(f"Failed to load from solve_config: {e}")

        # Fallback to question_config
        try:
            config = load_config_with_main("question_config.yaml", PROJECT_ROOT)
            run_code_config = config.get("tools", {}).get("run_code", {})
            if run_code_config:
                logger.debug("Loaded run_code config from question_config.yaml (with main.yaml)")
                return run_code_config
        except Exception as e:
            logger.debug(f"Failed to load from question_config: {e}")

        # Fallback to main.yaml only
        try:
            config = load_config_with_main("solve_config.yaml", PROJECT_ROOT)
            run_code_config = config.get("tools", {}).get("run_code", {})
            if run_code_config:
                return run_code_config
        except Exception:
            pass

    except ImportError:
        logger.debug("config_loader not available, using fallback")

    # Fallback: try loading main.yaml directly
    try:
        import yaml

        main_config_path = PROJECT_ROOT / "config" / "main.yaml"
        if main_config_path.exists():
            with open(main_config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            run_code_config = config.get("tools", {}).get("run_code", {})
            if run_code_config:
                logger.debug("Loaded run_code config from main.yaml")
                return run_code_config
    except Exception as e:
        logger.debug(f"Failed to load from main.yaml: {e}")

    return {}


class CodeExecutionError(Exception):
    """Code execution error"""


@dataclass
class OperationEntry:
    action: str
    details: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class OperationLogger:
    """Simple operation history logger, inspired by code_implementation_server recording method"""

    def __init__(self, max_entries: int = 200):
        self._history: list[OperationEntry] = []
        self._max_entries = max_entries

    def log(self, action: str, details: dict[str, Any]):
        entry = OperationEntry(action=action, details=details)
        self._history.append(entry)
        if len(self._history) > self._max_entries:
            self._history.pop(0)
        logger.debug(f"Operation logged: {action} | details={details.get('status')}")

    @property
    def history(self) -> list[OperationEntry]:
        return list(self._history)


class WorkspaceManager:
    """Manages isolated workspace, similar to code_implementation_server workspace logic"""

    def __init__(self):
        # Load configuration (priority: environment variable > config file > default)
        config = _load_config()

        # Determine workspace directory (priority: environment variable > config file > default)
        env_path = os.getenv(RUN_CODE_WORKSPACE_ENV)
        if env_path:
            self.base_dir = Path(env_path).expanduser().resolve()
        else:
            config_workspace = config.get("workspace")
            if config_workspace:
                # Support relative paths (relative to project root) and absolute paths
                workspace_path = Path(config_workspace).expanduser()
                if workspace_path.is_absolute():
                    self.base_dir = workspace_path.resolve()
                else:
                    self.base_dir = (PROJECT_ROOT / workspace_path).resolve()
            else:
                # Default workspace is set under user directory
                self.base_dir = (PROJECT_ROOT / "data" / "user" / DEFAULT_WORKSPACE_NAME).resolve()

        # Determine allowed root paths list
        # Default includes project root and user directory
        self.allowed_roots: list[Path] = [
            PROJECT_ROOT.resolve(),
            (PROJECT_ROOT / "data" / "user").resolve(),
        ]

        # Read allowed root paths from config file
        config_allowed_roots = config.get("allowed_roots", [])
        if isinstance(config_allowed_roots, str):
            config_allowed_roots = [config_allowed_roots]
        for root_path in config_allowed_roots:
            root = Path(root_path).expanduser()
            if root.is_absolute():
                resolved_root = root.resolve()
            else:
                resolved_root = (PROJECT_ROOT / root).resolve()
            # Avoid duplicate addition
            if resolved_root not in self.allowed_roots:
                self.allowed_roots.append(resolved_root)

        # Read additional allowed root paths from environment variables
        extra_roots = os.getenv(RUN_CODE_ALLOWED_ROOTS_ENV)
        if extra_roots:
            for raw_path in extra_roots.split(os.pathsep):
                raw_path = raw_path.strip()
                if raw_path:
                    path = Path(raw_path).expanduser()
                    if path.is_absolute():
                        resolved_path = path.resolve()
                    else:
                        resolved_path = (PROJECT_ROOT / path).resolve()
                    # Avoid duplicate addition
                    if resolved_path not in self.allowed_roots:
                        self.allowed_roots.append(resolved_path)

        # Ensure workspace directory itself can also be a valid root path
        if self.base_dir not in self.allowed_roots:
            self.allowed_roots.append(self.base_dir)

        self._initialized = False

    def initialize(self):
        if not self._initialized:
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self._initialized = True
            logger.info(f"Run-code workspace initialized at {self.base_dir}")

    def ensure_initialized(self):
        if not self._initialized:
            self.initialize()

    @contextmanager
    def create_temp_dir(self) -> Path:
        self.ensure_initialized()
        with tempfile.TemporaryDirectory(dir=self.base_dir) as temp_dir:
            yield Path(temp_dir)

    def resolve_assets_dir(self, assets_dir: str | None) -> Path | None:
        if not assets_dir:
            return None
        path = Path(assets_dir).expanduser()
        if not path.is_absolute():
            path = (self.base_dir / path).resolve()
        self._ensure_within_allowed_roots(path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def collect_artifacts(self, assets_dir: Path | None) -> tuple[list[str], list[str]]:
        artifacts: list[str] = []
        artifact_paths: list[str] = []
        if not assets_dir or not assets_dir.exists():
            return artifacts, artifact_paths

        for file_path in assets_dir.iterdir():
            if file_path.is_file() and file_path.name != ".gitkeep":
                artifacts.append(str(file_path.relative_to(assets_dir)))
                artifact_paths.append(str(file_path.resolve()))
        return artifacts, artifact_paths

    def _ensure_within_allowed_roots(self, path: Path):
        resolved_path = path.resolve()
        for root in self.allowed_roots:
            # Use Path object methods for path comparison, avoiding Windows path separator and case issues
            try:
                # Python 3.9+ use is_relative_to
                if hasattr(resolved_path, "is_relative_to"):
                    if resolved_path.is_relative_to(root):
                        return
                else:
                    # Python < 3.9 use path comparison after resolve()
                    # Convert to lowercase and normalize path separators for comparison (Windows compatible)
                    resolved_str = str(resolved_path).lower().replace("\\", "/")
                    root_str = str(root.resolve()).lower().replace("\\", "/")
                    if resolved_str.startswith(root_str):
                        return
            except (ValueError, AttributeError):
                # If is_relative_to fails, fallback to string comparison
                resolved_str = str(resolved_path).lower().replace("\\", "/")
                root_str = str(root.resolve()).lower().replace("\\", "/")
                if resolved_str.startswith(root_str):
                    return
        allowed = "\n".join(str(root) for root in self.allowed_roots)
        raise ValueError(
            f"Assets directory {resolved_path} must be located under one of the following allowed paths:\n{allowed}"
        )


class ImportGuard:
    """Parse AST, restrict import modules, ensure consistency with allowed_imports logic"""

    @staticmethod
    def validate(code: str, allowed_imports: list[str] | None):
        if not allowed_imports:
            return

        allowed = set(allowed_imports)
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            raise CodeExecutionError(f"Code syntax error: {exc}") from exc

        imported: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported.append(node.module.split(".")[0])

        unauthorized = sorted({name for name in imported if name not in allowed})
        if unauthorized:
            raise CodeExecutionError(
                f"The following modules are not in the allowed list: {', '.join(unauthorized)}"
            )


class CodeExecutionEnvironment:
    """Encapsulates actual code execution logic, maintaining consistency with DeepCode server flow"""

    def __init__(self, workspace: WorkspaceManager):
        self.workspace = workspace

    def run_python(
        self,
        code: str,
        timeout: int,
        assets_dir: Path | None,
    ) -> tuple[str, str, int, float]:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        with self.workspace.create_temp_dir() as temp_dir:
            code_file = temp_dir / "code.py"
            code_file.write_text(code, encoding="utf-8")

            work_dir = assets_dir if assets_dir else temp_dir
            start_time = time.time()

            result = subprocess.run(
                [sys.executable, str(code_file)],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=str(work_dir),
                env=env,
            )

            elapsed_ms = (time.time() - start_time) * 1000
            return result.stdout, result.stderr, result.returncode, elapsed_ms


WORKSPACE_MANAGER = WorkspaceManager()
OPERATION_LOGGER = OperationLogger()
EXECUTION_ENV = CodeExecutionEnvironment(WORKSPACE_MANAGER)


async def run_code(
    language: str,
    code: str,
    timeout: int = 10,
    assets_dir: str | None = None,
    allowed_imports: list[str] | None = None,
) -> dict[str, Any]:
    """
    Execute code in isolated environment, return result structure consistent with previous version.
    """
    if language.lower() != "python":
        raise ValueError(f"Unsupported language: {language}, currently only Python is supported")

    WORKSPACE_MANAGER.ensure_initialized()
    ImportGuard.validate(code, allowed_imports)

    assets_path = WORKSPACE_MANAGER.resolve_assets_dir(assets_dir)
    loop = asyncio.get_running_loop()

    def _execute():
        return EXECUTION_ENV.run_python(code, timeout, assets_path)

    try:
        stdout, stderr, exit_code, elapsed_ms = await loop.run_in_executor(None, _execute)
        artifacts, artifact_paths = WORKSPACE_MANAGER.collect_artifacts(assets_path)

        result = {
            "stdout": stdout,
            "stderr": stderr,
            "artifacts": artifacts,
            "artifact_paths": artifact_paths,
            "exit_code": exit_code,
            "elapsed_ms": elapsed_ms,
        }

        OPERATION_LOGGER.log(
            "execute_python",
            {
                "status": "success",
                "language": language,
                "timeout": timeout,
                "assets_dir": str(assets_path) if assets_path else None,
                "exit_code": exit_code,
                "elapsed_ms": elapsed_ms,
                "code_size": len(code),
            },
        )

        return result

    except subprocess.TimeoutExpired as timeout_exc:
        # Code execution timeout
        artifacts, artifact_paths = WORKSPACE_MANAGER.collect_artifacts(assets_path)
        elapsed_ms = timeout * 1000
        message = f"Code execution timeout ({timeout} seconds)"

        logger.warning(f"Code execution timeout after {timeout}s: {timeout_exc}")

        OPERATION_LOGGER.log(
            "execute_python",
            {
                "status": "timeout",
                "language": language,
                "timeout": timeout,
                "assets_dir": str(assets_path) if assets_path else None,
            },
        )

        return {
            "stdout": "",
            "stderr": message,
            "artifacts": artifacts,
            "artifact_paths": artifact_paths,
            "exit_code": -1,
            "elapsed_ms": elapsed_ms,
        }

    except Exception as exc:  # pylint: disable=broad-except
        # Catch all other exceptions to ensure main flow is not interrupted
        artifacts, artifact_paths = WORKSPACE_MANAGER.collect_artifacts(assets_path)
        elapsed_ms = 0.0

        if isinstance(exc, CodeExecutionError):
            stderr_message = str(exc)
        else:
            stderr_message = f"Code execution failed: {exc}"

        # Log detailed error information
        logger.error(f"Code execution error: {exc}", exc_info=True)

        OPERATION_LOGGER.log(
            "execute_python",
            {
                "status": "error",
                "language": language,
                "timeout": timeout,
                "assets_dir": str(assets_path) if assets_path else None,
                "error": stderr_message,
            },
        )

        return {
            "stdout": "",
            "stderr": stderr_message,
            "artifacts": artifacts,
            "artifact_paths": artifact_paths,
            "exit_code": -1,
            "elapsed_ms": elapsed_ms,
        }


def run_code_sync(
    language: str,
    code: str,
    timeout: int = 10,
    assets_dir: str | None = None,
) -> dict[str, Any]:
    """
    Synchronous version of code execution (for non-async environments)
    """

    return asyncio.run(run_code(language, code, timeout, assets_dir))


if __name__ == "__main__":
    import textwrap

    async def _demo():
        print("==== 1. Test normal output ====")
        sample1 = "print('Hello from run_code workspace!')"
        result1 = await run_code("python", sample1, timeout=5)
        print("stdout:", result1["stdout"])
        print("stderr:", result1["stderr"])
        print("artifacts:", result1.get("artifacts", {}))
        print("artifact_paths:", result1.get("artifact_paths", []))
        print("exit_code:", result1["exit_code"])
        print("-" * 40)

        print("==== 2. Test exception case ====")
        sample2 = "raise ValueError('Test error from run_code!')"
        result2 = await run_code("python", sample2, timeout=5)
        print("stdout:", result2["stdout"])
        print("stderr:", result2["stderr"])
        print("exit_code:", result2["exit_code"])
        print("-" * 40)

        print("==== 3. Test code timeout ====")
        sample3 = textwrap.dedent(
            """
        import time
        time.sleep(10)
        print("Timeout should occur before this prints.")
        """
        )
        result3 = await run_code("python", sample3, timeout=2)
        print("stdout:", result3["stdout"])
        print("stderr:", result3["stderr"])
        print("exit_code:", result3["exit_code"])
        print("-" * 40)

        print("==== 4. Test plotting functionality (matplotlib) ====")
        sample4 = textwrap.dedent(
            """
        import matplotlib.pyplot as plt
        plt.figure()
        plt.plot([1, 2, 3], [4, 2, 5])
        plt.title('Simple Plot')
        plt.savefig('test_plot.png')
        print('Plot created!')
        """
        )
        result4 = await run_code("python", sample4, timeout=5)
        print("stdout:", result4["stdout"])
        print("stderr:", result4["stderr"])
        print("artifacts:", result4.get("artifacts", {}))
        print("artifact_paths:", result4.get("artifact_paths", []))
        print("exit_code:", result4["exit_code"])
        # Check generated images
        if result4.get("artifact_paths"):
            print("Generated image files:", result4["artifact_paths"])
        else:
            print("No image files found.")
        print("-" * 40)

        print("==== 5. Test standard input ====")
        sample5 = textwrap.dedent(
            """
        text = input("Please enter content: ")
        print("You entered: ", text)
        """
        )
        # Standard run_code does not provide stdin, this example tests output behavior
        result5 = await run_code("python", sample5, timeout=5)
        print("stdout:", result5["stdout"])
        print("stderr:", result5["stderr"])
        print("exit_code:", result5["exit_code"])
        print("-" * 40)

        print("==== 6. Test multi-file and resource read/write ====")
        sample6 = textwrap.dedent(
            """
        with open('test_file.txt', 'w', encoding='utf-8') as f:
            f.write('Fake data for test!\\nAnother line.')
        with open('test_file.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        print('File content:', content)
        """
        )
        result6 = await run_code("python", sample6, timeout=5)
        print("stdout:", result6["stdout"])
        print("stderr:", result6["stderr"])
        print("artifacts:", result6.get("artifacts", {}))
        print("artifact_paths:", result6.get("artifact_paths", []))
        print("exit_code:", result6["exit_code"])
        print("-" * 40)

    asyncio.run(_demo())
