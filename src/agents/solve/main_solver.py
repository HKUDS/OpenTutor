#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main Solver - Problem-Solving System Controller

Based on Dual-Loop Architecture: Analysis Loop + Solve Loop
"""

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import traceback
from typing import Any

import yaml

# Add parent directory to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.services.config import load_config_with_main, parse_language
from src.services.llm import get_llm_config

from .analysis_loop import InvestigateAgent, NoteAgent

# Dual-Loop Architecture
from .memory import CitationMemory, InvestigateMemory, SolveChainStep, SolveMemory
from .solve_loop import (
    ManagerAgent,
    PrecisionAnswerAgent,
    ResponseAgent,
    SolveAgent,
    ToolAgent,
)
from .utils import ConfigValidator, PerformanceMonitor, SolveAgentLogger
from .utils.display_manager import get_display_manager
from .utils.token_tracker import TokenTracker


class MainSolver:
    """Problem-Solving System Controller"""

    def __init__(
        self,
        config_path: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        kb_name: str = "ai_textbook",
        output_base_dir: str | None = None,
    ):
        """
        Initialize MainSolver

        Args:
            config_path: Config file path (default: config.yaml in current directory)
            api_key: API key (if not provided, read from environment)
            base_url: API URL (if not provided, read from environment)
            api_version: API version (if not provided, read from environment)
            kb_name: Knowledge base name
            output_base_dir: Output base directory (optional, overrides config)
        """
        # Load config from config directory (main.yaml unified config)
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent.parent
            # Load main.yaml (solve_config.yaml is optional and will be merged if exists)
            full_config = load_config_with_main("main.yaml", project_root)

            # Extract solve-specific config and build validator-compatible structure
            solve_config = full_config.get("solve", {})
            paths_config = full_config.get("paths", {})

            # Build config structure expected by ConfigValidator
            self.config = {
                "system": {
                    "output_base_dir": paths_config.get("solve_output_dir", "./data/user/solve"),
                    "save_intermediate_results": solve_config.get(
                        "save_intermediate_results", True
                    ),
                    "language": full_config.get("system", {}).get("language", "en"),
                },
                "agents": solve_config.get("agents", {}),
                "logging": full_config.get("logging", {}),
                "tools": full_config.get("tools", {}),
                "paths": paths_config,
                # Keep solve-specific settings accessible
                "solve": solve_config,
            }
        else:
            # If custom config path provided, load it directly (for backward compatibility)
            local_config = {}
            if Path(config_path).exists():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        loaded = yaml.safe_load(f)
                        if loaded:
                            local_config = loaded
                except Exception:
                    # Config loading warning will be handled by config_loader
                    pass
            self.config = local_config if isinstance(local_config, dict) else {}

        if self.config is None or not isinstance(self.config, dict):
            self.config = {}

        # Override output directory config
        if output_base_dir:
            if "system" not in self.config:
                self.config["system"] = {}
            self.config["system"]["output_base_dir"] = str(output_base_dir)

            # Note: log_dir and performance_log_dir are now in paths section from main.yaml
            # Only override if explicitly needed

        # Validate config
        validator = ConfigValidator()
        is_valid, errors, warnings = validator.validate(self.config)
        if not is_valid:
            raise ValueError(f"Config validation failed: {errors}")

        # API config
        if api_key is None or base_url is None or "llm" not in self.config:
            try:
                llm_config = get_llm_config()
                if api_key is None:
                    api_key = llm_config.api_key
                if base_url is None:
                    base_url = llm_config.base_url
                if api_version is None:
                    api_version = getattr(llm_config, "api_version", None)

                # Ensure LLM config is populated in self.config for agents
                if "llm" not in self.config:
                    self.config["llm"] = {}

                # Update config with complete details (binding, model, etc.)
                from dataclasses import asdict

                self.config["llm"].update(asdict(llm_config))

            except ValueError as e:
                raise ValueError(f"LLM config error: {e!s}")

        # Check if API key is required
        # Local LLM servers (Ollama, LM Studio, etc.) don't need API keys
        from src.services.llm import is_local_llm_server

        if not api_key and not is_local_llm_server(base_url):
            raise ValueError("API key not set. Provide api_key param or set LLM_API_KEY in .env")

        # For local servers, use a placeholder key if none provided
        if not api_key and is_local_llm_server(base_url):
            api_key = "sk-no-key-required"

        self.api_key = api_key
        self.base_url = base_url
        self.api_version = api_version
        self.kb_name = kb_name

        # Initialize logging system
        logging_config = self.config.get("logging", {})
        # Get log_dir from paths (user_log_dir from main.yaml) or logging config
        log_dir = (
            self.config.get("paths", {}).get("user_log_dir")
            or self.config.get("paths", {}).get("log_dir")
            or logging_config.get("log_dir")
        )
        self.logger = SolveAgentLogger(
            name="Solver",
            level=logging_config.get("level", "INFO"),
            log_dir=log_dir,
            console_output=logging_config.get("console_output", True),
            file_output=logging_config.get("save_to_file", True),
        )

        # Attach display manager for TUI and frontend status updates
        self.logger.display_manager = get_display_manager()

        # Initialize performance monitor (disabled by default - performance logging is deprecated)
        monitoring_config = self.config.get("monitoring", {})
        # Disable performance monitor by default to avoid creating performance directory
        self.monitor = PerformanceMonitor(
            enabled=False,
            save_dir=None,  # Disabled - performance logging is deprecated
        )

        # Initialize Token tracker
        self.token_tracker = TokenTracker(prefer_tiktoken=True)

        # Connect token_tracker to display_manager for real-time updates
        if self.logger.display_manager:
            self.token_tracker.set_on_usage_added_callback(
                self.logger.display_manager.update_token_stats
            )

        self.logger.section("Dual-Loop Solver Initializing")
        self.logger.info(f"Knowledge Base: {kb_name}")

        # Initialize Agents
        self._init_agents()

        self.logger.success("Solver ready")

    def _deep_merge(self, base: dict, update: dict) -> dict:
        """Deep merge two dictionaries"""
        if base is None:
            base = {}
        if update is None:
            update = {}

        result = base.copy() if base else {}
        for key, value in update.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _init_agents(self):
        """Initialize all Agents - Dual-Loop Architecture"""
        self.logger.progress("Initializing agents...")

        # Analysis Loop Agents
        self.investigate_agent = InvestigateAgent(
            config=self.config,
            api_key=self.api_key,
            base_url=self.base_url,
            api_version=self.api_version,
            token_tracker=self.token_tracker,
        )
        self.logger.info("  InvestigateAgent initialized")

        self.note_agent = NoteAgent(
            config=self.config,
            api_key=self.api_key,
            base_url=self.base_url,
            api_version=self.api_version,
            token_tracker=self.token_tracker,
        )
        self.logger.info("  NoteAgent initialized")

        # Solve Loop Agents (lazy initialization)
        self.manager_agent = None
        self.solve_agent = None
        self.tool_agent = None
        self.response_agent = None
        self.precision_answer_agent = None
        self.logger.info("  Solve Loop agents (lazy init)")

    async def solve(self, question: str, verbose: bool = True) -> dict[str, Any]:
        """
        Main solving process - Dual-Loop Architecture

        Args:
            question: User question
            verbose: Whether to print detailed info

        Returns:
            dict: Solving result
        """
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_base_dir = self.config.get("system", {}).get("output_base_dir", "./user/solve")
        output_dir = os.path.join(output_base_dir, f"solve_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)

        # Add task log file handler
        task_log_file = os.path.join(output_dir, "task.log")
        self.logger.add_task_log_handler(task_log_file)

        self.logger.section("Problem Solving Started")
        self.logger.info(f"Question: {question[:100]}{'...' if len(question) > 100 else ''}")
        self.logger.info(f"Output: {output_dir}")

        try:
            # Execute dual-loop pipeline
            result = await self._run_dual_loop_pipeline(question, output_dir)

            # Add metadata
            result["metadata"] = {
                "mode": "dual_loop",
                "timestamp": timestamp,
                "output_dir": output_dir,
            }

            # Save performance report
            if self.config.get("monitoring", {}).get("enabled", True):
                perf_report = self.monitor.generate_report()
                perf_file = os.path.join(output_dir, "performance_report.json")
                with open(perf_file, "w", encoding="utf-8") as f:
                    json.dump(perf_report, f, ensure_ascii=False, indent=2)
                self.logger.debug(f"Performance report saved: {perf_file}")

            # Output cost report
            if self.token_tracker:
                cost_summary = self.token_tracker.get_summary()
                if cost_summary["total_calls"] > 0:
                    cost_text = self.token_tracker.format_summary()
                    self.logger.info(f"\n{cost_text}")

                    cost_file = os.path.join(output_dir, "cost_report.json")
                    self.token_tracker.save(cost_file)
                    self.logger.debug(f"Cost report saved: {cost_file}")

                    self.token_tracker.reset()

            self.logger.success("Problem solving completed")
            self.logger.remove_task_log_handlers()

            return result

        except Exception as e:
            self.logger.error(f"Solving failed: {e!s}")
            self.logger.error(traceback.format_exc())
            self.logger.remove_task_log_handlers()
            raise

        finally:
            if hasattr(self, "logger"):
                self.logger.shutdown()

    async def _run_dual_loop_pipeline(self, question: str, output_dir: str) -> dict[str, Any]:
        """
        Dual-Loop Pipeline:
        1) Analysis Loop: Investigate → Note
        2) Solve Loop: Plan → Manager → Solve → Check → Format
        """

        self.logger.info("Pipeline: Analysis Loop → Solve Loop")

        # ========== Analysis Loop ==========
        self.logger.stage("Analysis Loop", "start", "Understanding the question")

        investigate_memory = InvestigateMemory.load_or_create(
            output_dir=output_dir, user_question=question
        )

        citation_memory = CitationMemory.load_or_create(output_dir=output_dir)

        # Read max_iterations from solve.agents.investigate_agent config (authoritative source)
        agent_config = self.config.get("solve", {}).get("agents", {}).get("investigate_agent", {})
        max_analysis_iterations = agent_config.get("max_iterations", 5)
        self.logger.log_stage_progress(
            "AnalysisLoop", "start", f"max_iterations={max_analysis_iterations}"
        )

        analysis_completed = False

        # Analysis Loop iterations
        for i in range(max_analysis_iterations):
            self.logger.log_stage_progress("AnalysisLoop", "running", f"round={i + 1}")

            # 1. Investigate: Generate queries and call tools
            with self.monitor.track(f"analysis_investigate_{i + 1}"):
                investigate_result = await self.investigate_agent.process(
                    question=question,
                    memory=investigate_memory,
                    citation_memory=citation_memory,
                    kb_name=self.kb_name,
                    output_dir=output_dir,
                    verbose=False,
                )

            knowledge_ids: list[str] = investigate_result.get("knowledge_item_ids", [])
            should_stop = investigate_result.get("should_stop", False)
            reasoning = investigate_result.get("reasoning", "")
            actions = investigate_result.get("actions", [])

            self.logger.debug(f"  [Investigate] Reasoning: {reasoning or 'N/A'}")

            if hasattr(self, "_send_progress_update"):
                queries = [action.get("query", "") for action in actions if action.get("query")]
                self._send_progress_update("investigate", {"round": i + 1, "queries": queries})

            if actions:
                for action in actions:
                    tool_label = action["tool_type"]
                    query = action.get("query") or ""
                    cite_id = action.get("cite_id")
                    suffix = f" → cite_id={cite_id}" if cite_id else ""
                    self.logger.info(f"  Tool: {tool_label} | {query[:50]}{suffix}")
            else:
                self.logger.debug("  No queries generated this round")

            # 2. Note: Generate notes (if new knowledge exists)
            if knowledge_ids:
                self.logger.log_stage_progress("Note", "start")

                with self.monitor.track(f"analysis_note_{i + 1}"):
                    note_result = await self.note_agent.process(
                        question=question,
                        memory=investigate_memory,
                        new_knowledge_ids=knowledge_ids,
                        citation_memory=citation_memory,
                        output_dir=output_dir,
                        verbose=False,
                    )

                if note_result.get("success"):
                    processed = note_result.get("processed_items", 0)
                    self.logger.info(f"  Note: {processed} items processed")
                    self.logger.log_stage_progress("Note", "complete")
                else:
                    self.logger.warning(f"  Note failed: {note_result.get('reason', 'unknown')}")
                    self.logger.log_stage_progress("Note", "error")

            # Update Token stats
            self.logger.update_token_stats(self.token_tracker.get_summary())

            # 3. Check stop condition
            if should_stop:
                analysis_completed = True
                self.logger.log_stage_progress(
                    "AnalysisLoop",
                    "complete",
                    f"rounds={i + 1}, knowledge={len(investigate_memory.knowledge_chain)}",
                )
                break

        if not analysis_completed:
            self.logger.log_stage_progress(
                "AnalysisLoop",
                "warning",
                f"max_iterations({max_analysis_iterations}) reached, knowledge={len(investigate_memory.knowledge_chain)}",
            )

        # Update investigate_memory metadata
        investigate_memory.metadata["total_iterations"] = i + 1
        investigate_memory.metadata["total_knowledge_items"] = len(
            investigate_memory.knowledge_chain
        )
        investigate_memory.reflections.remaining_questions = []

        if analysis_completed:
            investigate_memory.metadata["coverage_rate"] = 1.0
            investigate_memory.metadata["avg_confidence"] = 0.9
        else:
            coverage = min(
                1.0, len(investigate_memory.knowledge_chain) / max(1, max_analysis_iterations)
            )
            investigate_memory.metadata["coverage_rate"] = coverage
            investigate_memory.metadata["avg_confidence"] = 0.6

        investigate_memory.save()

        # ========== Solve Loop ==========
        self.logger.stage("Solve Loop", "start", "Generating solution")

        solve_memory = SolveMemory.load_or_create(output_dir=output_dir, user_question=question)

        # Initialize Solve Loop Agents (if not yet initialized)
        if self.manager_agent is None:
            self.logger.progress("Initializing Solve Loop agents...")
            self.manager_agent = ManagerAgent(
                self.config,
                self.api_key,
                self.base_url,
                api_version=self.api_version,
                token_tracker=self.token_tracker,
            )
            self.solve_agent = SolveAgent(
                self.config,
                self.api_key,
                self.base_url,
                api_version=self.api_version,
                token_tracker=self.token_tracker,
            )
            self.tool_agent = ToolAgent(
                self.config,
                self.api_key,
                self.base_url,
                api_version=self.api_version,
                token_tracker=self.token_tracker,
            )
            self.response_agent = ResponseAgent(
                self.config,
                self.api_key,
                self.base_url,
                api_version=self.api_version,
                token_tracker=self.token_tracker,
            )

            precision_enabled = (
                self.config.get("agents", {})
                .get("precision_answer_agent", {})
                .get("enabled", False)
            )
            if precision_enabled:
                self.precision_answer_agent = PrecisionAnswerAgent(
                    self.config,
                    self.api_key,
                    self.base_url,
                    api_version=self.api_version,
                    token_tracker=self.token_tracker,
                )

        # 1. Plan: Generate solving plan
        self.logger.info("Plan: Generating solution strategy...")

        plan_result = None
        for attempt in range(2):
            try:
                with self.monitor.track(f"solve_plan_attempt_{attempt + 1}"):
                    plan_result = await self.manager_agent.process(
                        question=question,
                        investigate_memory=investigate_memory,
                        solve_memory=solve_memory,
                        verbose=(attempt > 0),
                    )
                num_steps = plan_result.get("num_steps") or plan_result.get("steps_count", 0)
                self.logger.log_stage_progress("Plan", "complete", f"steps={num_steps}")
                self.logger.update_token_stats(self.token_tracker.get_summary())
                break
            except Exception as e:
                if attempt == 0:
                    self.logger.error(f"ManagerAgent attempt {attempt + 1} failed: {e!s}")
                    self.logger.warning("Retrying plan generation...")
                    solve_memory = SolveMemory.load_or_create(
                        output_dir=output_dir, user_question=question
                    )
                else:
                    self.logger.error(f"ManagerAgent attempt {attempt + 1} also failed")
                    raise ValueError(f"ManagerAgent failed after retry: {e!s}")

        if plan_result is None:
            raise ValueError("ManagerAgent failed to generate plan")

        # 2. Solve Loop - Execute steps
        self.logger.info("Solve: Executing solution steps...")
        max_correction_iterations = self.config.get("system", {}).get(
            "max_solve_correction_iterations", 3
        )
        total_planned_steps = len(solve_memory.solve_chains)
        self.logger.log_stage_progress(
            "SolveLoop",
            "start",
            f"planned_steps={total_planned_steps}, max_corrections={max_correction_iterations}",
        )

        for step_index, step in enumerate(solve_memory.solve_chains, 1):
            if step.status in ("waiting_response", "done"):
                continue

            self.logger.info(f"  Step {step_index}: {step.step_id}")
            self.logger.debug(f"  Target: {step.step_target[:80]}")

            if hasattr(self, "_send_progress_update"):
                self._send_progress_update(
                    "solve",
                    {
                        "step_index": step_index,
                        "step_id": step.step_id,
                        "step_target": step.step_target,
                    },
                )

            self.logger.log_stage_progress("SolveLoop", "running", f"step={step.step_id}")

            if self._has_pending_tool_calls(step):
                await self._execute_tool_calls(step, solve_memory, citation_memory, output_dir)

            iteration = 0
            while iteration < max_correction_iterations:
                iteration += 1
                current_step = solve_memory.get_step(step.step_id) or step

                with self.monitor.track(f"solve_execute_{step.step_id}_iter_{iteration}"):
                    solve_result = await self.solve_agent.process(
                        question=question,
                        current_step=current_step,
                        solve_memory=solve_memory,
                        investigate_memory=investigate_memory,
                        citation_memory=citation_memory,
                        kb_name=self.kb_name,
                        output_dir=output_dir,
                        verbose=False,
                    )

                if solve_result.get("raw_llm_response"):
                    self.logger.log_stage_progress(
                        "SolveLoop", "running", f"step={step.step_id}, iteration={iteration}"
                    )

                if solve_result.get("requested_calls"):
                    await self._execute_tool_calls(
                        current_step, solve_memory, citation_memory, output_dir
                    )

                self.logger.update_token_stats(self.token_tracker.get_summary())

                if solve_result.get("finish_requested"):
                    current_step = solve_memory.get_step(step.step_id) or step
                    if self._has_pending_tool_calls(current_step):
                        self.logger.debug("  Finish triggered but tools pending, continuing...")
                        continue
                    solve_memory.mark_step_waiting_response(current_step.step_id)
                    solve_memory.save()
                    self.logger.log_stage_progress(
                        "SolveLoop", "complete", f"step={current_step.step_id} ready for response"
                    )
                    break
            else:
                self.logger.warning(f"  Step {step.step_id} max iterations reached")
                solve_memory.mark_step_waiting_response(step.step_id)
                solve_memory.save()

        pending_steps = [
            s.step_id
            for s in solve_memory.solve_chains
            if s.status not in ("waiting_response", "done")
        ]
        if pending_steps:
            self.logger.warning(f"Steps not ready for response: {', '.join(pending_steps)}")

        self.logger.log_stage_progress(
            "SolveLoop", "complete", f"steps_processed={total_planned_steps - len(pending_steps)}"
        )

        # 3. Response: Generate responses for each step
        self.logger.info("Response: Generating step responses...")
        self.logger.log_stage_progress("ResponseLoop", "start", "Generating responses")

        accumulated_response = ""
        for step in solve_memory.solve_chains:
            if step.status == "done" and step.step_response:
                accumulated_response += step.step_response + "\n\n"

        for step in solve_memory.solve_chains:
            if step.status != "waiting_response":
                continue

            original_step_index = next(
                (
                    i + 1
                    for i, s in enumerate(solve_memory.solve_chains)
                    if s.step_id == step.step_id
                ),
                0,
            )

            if hasattr(self, "_send_progress_update"):
                self._send_progress_update(
                    "response",
                    {
                        "step_index": original_step_index,
                        "step_id": step.step_id,
                        "step_target": step.step_target,
                    },
                )

            with self.monitor.track(f"solve_response_{step.step_id}"):
                response_result = await self.response_agent.process(
                    question=question,
                    step=step,
                    solve_memory=solve_memory,
                    investigate_memory=investigate_memory,
                    citation_memory=citation_memory,
                    output_dir=output_dir,
                    verbose=False,
                    accumulated_response=accumulated_response,
                )

            step_response = response_result.get("step_response", "")
            if step_response:
                accumulated_response += step_response + "\n\n"

            if response_result.get("raw_response"):
                self.logger.log_stage_progress(
                    "ResponseLoop", "running", f"step={step.step_id} response generated"
                )

            self.logger.update_token_stats(self.token_tracker.get_summary())

        self.logger.log_stage_progress("ResponseLoop", "complete", "All responses generated")

        # 4. Finalize: Compile final answer
        self.logger.info("Finalize: Compiling final answer...")
        self.logger.log_stage_progress("Finalize", "start", "Compiling steps")

        actual_total_steps = len(solve_memory.solve_chains)
        completed_step_objs = [
            step
            for step in solve_memory.solve_chains
            if step.status == "done" and step.step_response
        ]
        completed_steps = len(completed_step_objs)

        solve_memory.metadata["total_steps"] = actual_total_steps
        solve_memory.metadata["completed_steps"] = completed_steps
        solve_memory.save()
        self.logger.info(f"  Stats: {completed_steps}/{actual_total_steps} steps completed")

        used_cite_ids = []
        for step in completed_step_objs:
            used_cite_ids.extend(step.used_citations)
        used_cite_ids = list(dict.fromkeys(used_cite_ids))

        step_responses = [step.step_response for step in completed_step_objs]
        final_answer = "\n\n".join(step_responses)

        # Get language setting from config (unified in config/main.yaml system.language)
        language = self.config.get("system", {}).get("language", "zh")
        lang_code = parse_language(language)

        # Check if citations are enabled
        enable_citations = self.config.get("system", {}).get("enable_citations", True)

        citations_section = ""
        if enable_citations and citation_memory:
            citations_section = citation_memory.format_citations_markdown(
                used_cite_ids=used_cite_ids, language=lang_code
            )
            if citations_section:
                final_answer = f"{final_answer}\n\n---\n\n{citations_section}"

        format_result = {
            "final_answer": final_answer.strip(),
            "citations": used_cite_ids,
            "metadata": {
                "refined_steps": len(completed_step_objs),
                "total_steps": actual_total_steps,
                "citations_section": bool(citations_section),
            },
        }

        self.logger.info(f"  Final answer: {len(format_result['final_answer'])} chars")
        self.logger.info(f"  Citations: {len(format_result['citations'])}")

        # 5. Precision Answer (if enabled)
        precision_answer_enabled = (
            self.config.get("agents", {}).get("precision_answer_agent", {}).get("enabled", False)
        )
        final_answer_content = format_result["final_answer"]

        if precision_answer_enabled and self.precision_answer_agent:
            self.logger.info("PrecisionAnswer: Generating concise answer...")
            with self.monitor.track("precision_answer"):
                precision_result = await self.precision_answer_agent.process(
                    question=question, detailed_answer=format_result["final_answer"], verbose=False
                )
            if precision_result.get("needs_precision"):
                precision_answer = precision_result.get("precision_answer", "")
                self.logger.info(f"  Precision answer: {len(precision_answer)} chars")
                final_answer_content = f"## Concise Answer\n\n{precision_answer}\n\n---\n\n## Detailed Answer\n\n{format_result['final_answer']}"
            else:
                self.logger.debug("  No precision answer needed")

        # Save final answer
        final_answer_file = Path(output_dir) / "final_answer.md"
        with open(final_answer_file, "w", encoding="utf-8") as f:
            f.write(final_answer_content)

        self.logger.success(f"Final answer saved: {final_answer_file}")
        self.logger.log_stage_progress("Format", "complete", f"output={final_answer_file}")

        return {
            "question": question,
            "output_dir": output_dir,
            "final_answer": final_answer_content,
            "output_md": str(final_answer_file),
            "output_json": str(Path(output_dir) / "solve_chain.json"),
            "formatted_solution": final_answer_content,
            "citations": format_result["citations"],
            "pipeline": "reworked",
            "total_steps": solve_memory.metadata["total_steps"],
            "analysis_iterations": investigate_memory.metadata.get("total_iterations", 0),
            "solve_steps": solve_memory.metadata["completed_steps"],
            "metadata": {
                "coverage_rate": investigate_memory.metadata.get("coverage_rate", 0.0),
                "avg_confidence": investigate_memory.metadata.get("avg_confidence", 0.0),
                "total_steps": solve_memory.metadata["total_steps"],
            },
        }

    async def _execute_tool_calls(
        self,
        step: SolveChainStep,
        solve_memory: SolveMemory,
        citation_memory: CitationMemory,
        output_dir: str | None,
    ) -> dict[str, Any]:
        tool_result = await self.tool_agent.process(
            step=step,
            solve_memory=solve_memory,
            citation_memory=citation_memory,
            kb_name=self.kb_name,
            output_dir=output_dir,
            verbose=False,
        )
        return tool_result

    @staticmethod
    def _has_pending_tool_calls(step: SolveChainStep) -> bool:
        return any(call.status in {"pending", "running"} for call in step.tool_calls)


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    async def test():
        solver = MainSolver(kb_name="ai_textbook")
        result = await solver.solve(question="What is linear convolution?", verbose=True)
        print(f"Output file: {result['output_md']}")

    asyncio.run(test())
