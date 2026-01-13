#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Config Validator - Configuration validator
Validates the completeness and correctness of config.yaml
"""

from pathlib import Path
from typing import Any

import yaml


class ConfigValidator:
    """Configuration validator"""

    # Required top-level configuration items
    # Note: llm configuration has been moved to environment variables (env_config.py), no longer required in config.yaml
    REQUIRED_SECTIONS = ["system", "agents"]

    # Required system configuration
    REQUIRED_SYSTEM_CONFIGS = [
        "output_base_dir",
        "save_intermediate_results",
        # Note: language is now unified in config/main.yaml, not required in sub-configs
    ]

    # Supported languages (supports multiple formats)
    SUPPORTED_LANGUAGES = ["zh", "en", "English", "Chinese"]

    # Supported log levels
    SUPPORTED_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    # Agent list - dual-loop architecture
    STANDARD_AGENTS = [
        # Analysis Loop
        "investigate_agent",
        "note_agent",
        # Solve Loop
        "manager_agent",
        "solve_agent",
        "tool_agent",
        "response_agent",
        "precision_answer_agent",
    ]

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def validate(self, config: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
        """
        Validate configuration

        Args:
            config: Configuration dictionary

        Returns:
            (is_valid, errors, warnings)
        """
        self.errors = []
        self.warnings = []

        # 1. Validate top-level structure
        self._validate_structure(config)

        # 2. Validate system configuration
        if "system" in config:
            self._validate_system(config["system"])

        # 3. Validate agents configuration
        if "agents" in config:
            self._validate_agents(config["agents"])

        # 4. Validate llm configuration (optional, LLM config now mainly comes from environment variables)
        if "llm" in config:
            self._validate_llm(config["llm"])

        # 5. Validate logging configuration (optional)
        if "logging" in config:
            self._validate_logging(config["logging"])

        # 6. Validate monitoring configuration (optional)
        if "monitoring" in config:
            self._validate_monitoring(config["monitoring"])

        is_valid = len(self.errors) == 0
        return is_valid, self.errors, self.warnings

    def _validate_structure(self, config: dict[str, Any]):
        """Validate top-level structure"""
        for section in self.REQUIRED_SECTIONS:
            if section not in config:
                self.errors.append(f"Missing required configuration section: {section}")

    def _validate_system(self, system_config: dict[str, Any]):
        """Validate system configuration"""
        if system_config is None:
            self.errors.append("system configuration cannot be None")
            return

        # Check required fields
        for field in self.REQUIRED_SYSTEM_CONFIGS:
            if field not in system_config:
                self.errors.append(f"system config missing required field: {field}")

        # Check language configuration (unified in config/main.yaml, optional in sub-configs)
        if "language" in system_config:
            lang = system_config["language"]
            if lang not in self.SUPPORTED_LANGUAGES:
                self.warnings.append(
                    f"language '{lang}' not in supported list: {self.SUPPORTED_LANGUAGES}. Suggest unified configuration in config/main.yaml."
                )
        # Backward compatibility: if output_language still exists, give warning
        if "output_language" in system_config:
            self.warnings.append(
                "output_language is deprecated, please use language field. Language configuration has been unified to system.language in config/main.yaml"
            )

        # Check auto_solve configuration
        if "auto_solve" in system_config:
            if not isinstance(system_config["auto_solve"], bool):
                self.errors.append("auto_solve must be a boolean value")

    def _validate_agents(self, agents_config: dict[str, Any]):
        """Validate agents configuration"""
        if agents_config is None:
            self.errors.append("agents config cannot be None")
            return

        # Check if standard agents are configured
        for agent_name in self.STANDARD_AGENTS:
            if agent_name not in agents_config:
                self.warnings.append(f"Agent not configured: {agent_name}")
            else:
                self._validate_agent_config(agent_name, agents_config[agent_name])

    def _validate_agent_config(self, agent_name: str, agent_config: dict[str, Any]):
        """Validate single Agent configuration"""
        if agent_config is None:
            self.errors.append(f"{agent_name} config cannot be None")
            return

        # Check enabled field
        if "enabled" in agent_config:
            if not isinstance(agent_config["enabled"], bool):
                self.errors.append(f"{agent_name}.enabled must be a boolean value")

        # Check model field
        if "model" in agent_config:
            if not isinstance(agent_config["model"], str):
                self.errors.append(f"{agent_name}.model must be a string")

        # Check temperature field
        if "temperature" in agent_config:
            temp = agent_config["temperature"]
            if not isinstance(temp, (int, float)):
                self.errors.append(f"{agent_name}.temperature must be a number")
            elif not 0 <= temp <= 2:
                self.warnings.append(
                    f"{agent_name}.temperature={temp} exceeds recommended range [0, 2]"
                )

        # Check max_retries field
        if "max_retries" in agent_config:
            if not isinstance(agent_config["max_retries"], int):
                self.errors.append(f"{agent_name}.max_retries must be an integer")
            elif agent_config["max_retries"] < 0:
                self.errors.append(f"{agent_name}.max_retries cannot be negative")

    def _validate_llm(self, llm_config: dict[str, Any]):
        """Validate llm configuration"""
        if llm_config is None:
            self.errors.append("llm config cannot be None")
            return

        # Check default_model
        if "default_model" not in llm_config:
            self.warnings.append("llm config missing default_model field")

        # Check max_retries
        if "max_retries" in llm_config:
            if not isinstance(llm_config["max_retries"], int):
                self.errors.append("llm.max_retries must be an integer")
            elif llm_config["max_retries"] < 0:
                self.errors.append("llm.max_retries cannot be negative")

        # Check timeout
        if "timeout" in llm_config:
            if not isinstance(llm_config["timeout"], (int, float)):
                self.errors.append("llm.timeout must be a number")
            elif llm_config["timeout"] <= 0:
                self.warnings.append("llm.timeout should not be negative or zero")

    def _validate_logging(self, logging_config: dict[str, Any]):
        """Validate logging configuration"""
        if logging_config is None:
            # logging is optional, if None but not empty key, may be considered error or ignored
            self.errors.append("logging config cannot be None")
            return

        # Check level
        if "level" in logging_config:
            level = logging_config["level"]
            if level not in self.SUPPORTED_LOG_LEVELS:
                self.errors.append(
                    f"logging.level '{level}' not in supported list: {self.SUPPORTED_LOG_LEVELS}"
                )

        # Check save_to_file
        if "save_to_file" in logging_config:
            if not isinstance(logging_config["save_to_file"], bool):
                self.errors.append("logging.save_to_file must be a boolean value")

        # Check verbose
        if "verbose" in logging_config:
            if not isinstance(logging_config["verbose"], bool):
                self.errors.append("logging.verbose must be a boolean value")

    def _validate_monitoring(self, monitoring_config: dict[str, Any]):
        """Validate monitoring configuration"""
        if monitoring_config is None:
            self.errors.append("monitoring config cannot be None")
            return

        # Check enabled
        if "enabled" in monitoring_config:
            if not isinstance(monitoring_config["enabled"], bool):
                self.errors.append("monitoring.enabled must be a boolean value")

        # Check track_token_usage
        if "track_token_usage" in monitoring_config:
            if not isinstance(monitoring_config["track_token_usage"], bool):
                self.errors.append("monitoring.track_token_usage must be a boolean value")

        # Check track_time
        if "track_time" in monitoring_config:
            if not isinstance(monitoring_config["track_time"], bool):
                self.errors.append("monitoring.track_time must be a boolean value")


def validate_config_file(config_path: str) -> tuple[bool, list[str], list[str]]:
    """
    Validate configuration file

    Args:
        config_path: Configuration file path

    Returns:
        (is_valid, errors, warnings)
    """
    try:
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        return False, [f"Configuration file does not exist: {config_path}"], []
    except yaml.YAMLError as e:
        return False, [f"YAML parsing error: {e!s}"], []
    except Exception as e:
        return False, [f"Failed to load configuration file: {e!s}"], []

    validator = ConfigValidator()
    return validator.validate(config)


def print_validation_result(is_valid: bool, errors: list[str], warnings: list[str]):
    """
    Print validation result

    Args:
        is_valid: Whether configuration is valid
        errors: List of errors
        warnings: List of warnings
    """
    print("=" * 60)
    print("Configuration Validation Result")
    print("=" * 60)

    if is_valid:
        print("✓ Configuration validation passed")
    else:
        print("✗ Configuration validation failed")

    print()

    if errors:
        print(f"Errors ({len(errors)}):")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")
        print()

    if warnings:
        print(f"Warnings ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
        print()

    print("=" * 60)


if __name__ == "__main__":
    # Test configuration validation
    print("Configuration Validation Test")
    print("=" * 60)

    # Validate config.yaml in current directory
    config_path = Path(__file__).parent.parent.parent.parent / "config.yaml"

    if config_path.exists():
        is_valid, errors, warnings = validate_config_file(str(config_path))
        print_validation_result(is_valid, errors, warnings)
    else:
        print(f"Configuration file not found: {config_path}")
