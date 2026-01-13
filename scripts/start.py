#!/usr/bin/env python
"""
DeepTutor CLI Launcher

Provides a command-line interface for users to easily access:
1. Solver system (solve_agents)
2. Question generation system (question_agents)
3. Deep research system (DR-in-KG)
"""

import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv

# Set Windows console UTF-8 encoding
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Load environment variables
load_dotenv()

# Add project root directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.question import AgentCoordinator
from src.agents.solve import MainSolver
from src.api.utils.history import ActivityType, history_manager
from src.logging import get_logger
from src.services.llm import get_llm_config

# Initialize logger for CLI
logger = get_logger("CLI", console_output=True, file_output=True)


class AITutorStarter:
    """DeepTutor CLI Launcher"""

    def __init__(self):
        """Initialize launcher"""
        # Initialize user data directories
        try:
            from src.services.setup import init_user_directories

            init_user_directories(project_root)
        except Exception as e:
            logger.warning(f"Failed to initialize user directories: {e}")
            logger.info("Continuing anyway...")

        try:
            llm_config = get_llm_config()
            self.api_key = llm_config.api_key
            self.base_url = llm_config.base_url
        except ValueError as e:
            logger.error(str(e))
            logger.error("Please configure LLM settings in .env or DeepTutor.env file")
            sys.exit(1)

        # Load knowledge base list
        self.available_kbs = self._load_available_kbs()

        logger.section("DeepTutor Intelligent Teaching Assistant System")
        logger.success("API configuration loaded")
        logger.info(f"Available knowledge bases: {', '.join(self.available_kbs)}")
        logger.separator()

    def _load_available_kbs(self) -> list:
        """Load available knowledge base list"""
        kb_base_dir = Path(__file__).parent / "data/knowledge_bases"
        if not kb_base_dir.exists():
            return ["ai_textbook"]  # Default knowledge base

        # Read configuration file
        kb_config_file = kb_base_dir / "kb_config.json"
        if kb_config_file.exists():
            import json

            with open(kb_config_file, encoding="utf-8") as f:
                config = json.load(f)
                return list(config.get("knowledge_bases", {}).keys())

        # Otherwise scan directory
        kbs = []
        for item in kb_base_dir.iterdir():
            if item.is_dir() and not item.name.startswith("."):
                kbs.append(item.name)

        return kbs if kbs else ["ai_textbook"]

    def show_main_menu(self) -> str:
        """Display main menu and get user selection"""
        logger.section("Please select a function:")
        print("1. 🧠 Solver System (Solve)        - Intelligent academic problem solving")
        print(
            "2. 📝 Question Generator (Question)     - Generate questions based on knowledge base"
        )
        print("3. 🔬 Deep Research (Research)     - Multi-round deep knowledge research")
        print("4. 💡 Idea Generation (IdeaGen)      - Extract research ideas from notes")
        print("5. 🌐 Start Web Service (Web)       - Start frontend and backend services")
        print("6. ⚙️  System Settings (Settings)     - View/modify configuration")
        print("7. 🚪 Exit")
        logger.separator()

        while True:
            choice = input("\nPlease enter option (1-7): ").strip()
            if choice in ["1", "2", "3", "4", "5", "6", "7"]:
                return choice
            logger.warning("Invalid option, please try again")

    def select_kb(self, default: str = None) -> str:
        """Select knowledge base"""
        if len(self.available_kbs) == 1:
            return self.available_kbs[0]

        logger.separator()
        logger.info("Available knowledge bases:")
        logger.separator()
        for i, kb in enumerate(self.available_kbs, 1):
            default_mark = " (default)" if kb == default else ""
            print(f"{i}. {kb}{default_mark}")
        logger.separator()

        while True:
            choice = input(
                f"\nPlease select knowledge base (1-{len(self.available_kbs)}) [default: 1]: "
            ).strip()
            if not choice:
                return self.available_kbs[0]

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(self.available_kbs):
                    return self.available_kbs[idx]
                logger.warning(f"Please enter a number between 1 and {len(self.available_kbs)}")
            except ValueError:
                logger.warning("Please enter a valid number")

    async def run_solve_mode(self):
        """Run solver mode"""
        logger.section("Solver System")

        # Select knowledge base
        kb_name = self.select_kb(default="ai_textbook")
        logger.success(f"Selected knowledge base: {kb_name}")

        # Input question
        logger.separator()
        logger.info(
            "Please enter your question (multi-line input supported, empty line to finish):"
        )
        logger.separator()

        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)

        if not lines:
            logger.warning("No question entered, returning to main menu")
            return

        question = "\n".join(lines)

        # Display solver mode description
        logger.separator()
        logger.info("Solver Mode: Dual-Loop Architecture")
        logger.separator()
        logger.info("Analysis Loop: Deep understanding of user question")
        logger.info("   Investigate → Note")
        logger.info("")
        logger.info("Solve Loop: Collaborative solving")
        logger.info("   Manager → Solve → Tool → Response → Precision")
        logger.separator()

        logger.section("Starting solver...")

        try:
            # Create solver
            solver = MainSolver(
                config_path=None,  # Use default configuration file
                api_key=self.api_key,
                base_url=self.base_url,
                kb_name=kb_name,
            )

            # Run solver
            result = await solver.solve(question=question, verbose=True)

            logger.section("Solving completed!")
            logger.info(f"Output directory: {result['metadata']['output_dir']}")

            logger.info("Solving statistics:")
            logger.info(f"   Execution mode: {result['metadata']['mode']}")
            logger.info(f"   Pipeline: {result.get('pipeline', 'dual_loop')}")

            if "analysis_iterations" in result:
                logger.info(f"   Analysis loop iterations: {result['analysis_iterations']} rounds")
            if "solve_steps" in result:
                logger.info(f"   Solve steps completed: {result['solve_steps']} steps")
            if "total_steps" in result:
                logger.info(f"   Total planned steps: {result['total_steps']}")
            if "citations" in result:
                logger.info(f"   Citation count: {len(result['citations'])}")

            logger.info("Output files:")
            logger.info(f"   Markdown: {result['output_md']}")
            logger.info(f"   JSON: {result['output_json']}")
            logger.separator()

            # Display answer preview
            formatted_solution = result.get("formatted_solution", "")
            if formatted_solution:
                logger.separator()
                logger.info("Answer preview:")
                logger.separator()
                preview_lines = formatted_solution.split("\n")[:20]
                preview = "\n".join(preview_lines)
                if len(formatted_solution) > len(preview):
                    preview += "\n\n... (more content available in output file) ..."
                print(preview)
                logger.separator()

            # Save to history
            try:
                history_manager.add_entry(
                    activity_type=ActivityType.SOLVE,
                    title=question[:50] + "..." if len(question) > 50 else question,
                    content={
                        "question": question,
                        "answer": result.get("formatted_solution", ""),
                        "output_dir": result["metadata"]["output_dir"],
                        "kb_name": kb_name,
                        "metadata": result.get("metadata", {}),
                    },
                    summary=(
                        formatted_solution[:100] + "..."
                        if formatted_solution and len(formatted_solution) > 100
                        else (formatted_solution or "")
                    ),
                )
            except Exception as hist_error:
                # History save failure does not affect main flow
                logger.warning(f"History save failed: {hist_error!s}")

        except Exception as e:
            logger.section("Solving failed")
            logger.error(str(e))
            import traceback

            logger.debug("Debug information:")
            logger.debug(traceback.format_exc())

    async def run_question_mode(self):
        """Run question generation mode"""
        print("\n" + "=" * 70)
        print("📝 Question Generation System")
        print("=" * 70)

        # Select knowledge base
        kb_name = self.select_kb(default="ai_textbook")
        print(f"✅ Selected knowledge base: {kb_name}")

        # Input knowledge point
        print("\n" + "-" * 70)
        print("Please enter knowledge point:")
        print("-" * 70)
        knowledge_point = input().strip()

        if not knowledge_point:
            print("❌ No knowledge point entered, returning to main menu")
            return

        # Select difficulty
        print("\n" + "-" * 70)
        print("📊 Difficulty selection:")
        print("-" * 70)
        print("1. Easy")
        print("2. Medium")
        print("3. Hard")
        print("-" * 70)

        difficulty_map = {"1": "easy", "2": "medium", "3": "hard"}
        while True:
            diff_choice = input("\nPlease select difficulty (1-3) [default: 2]: ").strip()
            if not diff_choice:
                difficulty = "medium"
                break
            if diff_choice in difficulty_map:
                difficulty = difficulty_map[diff_choice]
                break
            print("❌ Invalid option, please try again")

        # Select question type
        print("\n" + "-" * 70)
        print("📋 Question type selection:")
        print("-" * 70)
        print("1. Multiple choice (choice)")
        print("2. Written answer (written)")
        print("-" * 70)

        while True:
            type_choice = input("\nPlease select question type (1/2) [default: 1]: ").strip()
            if not type_choice or type_choice == "1":
                question_type = "choice"
                break
            if type_choice == "2":
                question_type = "written"
                break
            print("❌ Invalid option, please try again")

        print("\n" + "=" * 70)
        print("🚀 Starting question generation...")
        print("=" * 70)

        try:
            # Create coordinator
            coordinator = AgentCoordinator(
                api_key=self.api_key,
                base_url=self.base_url,
                kb_name=kb_name,
                output_dir="./user/question",
            )

            # Build requirement
            requirement = {
                "knowledge_point": knowledge_point,
                "difficulty": difficulty,
                "question_type": question_type,
                "additional_requirements": "Ensure questions are clear and academically rigorous",
            }

            # Run question generation
            result = await coordinator.generate_question(requirement)

            if result.get("success"):
                print("\n" + "=" * 70)
                print("✅ Question generation completed!")
                print("=" * 70)

                question_data = result.get("question", {})
                print("\n📝 Question:")
                print(question_data.get("question", ""))

                if question_data.get("options"):
                    print("\n📋 Options:")
                    for key, value in question_data.get("options", {}).items():
                        print(f"  {key}. {value}")

                print(f"\n✅ Answer: {question_data.get('correct_answer', '')}")
                print("\n💡 Explanation:")
                print(question_data.get("explanation", ""))

                if result.get("output_dir"):
                    print(f"\n📁 Output directory: {result['output_dir']}")

                print("=" * 70)

                # Save to history
                try:
                    history_manager.add_entry(
                        activity_type=ActivityType.QUESTION,
                        title=f"{knowledge_point} ({question_type})",
                        content={
                            "requirement": requirement,
                            "question": question_data,
                            "output_dir": result.get("output_dir", ""),
                            "kb_name": kb_name,
                        },
                        summary=(
                            question_data.get("question", "")[:100] + "..."
                            if len(question_data.get("question", "")) > 100
                            else question_data.get("question", "")
                        ),
                    )
                except Exception as hist_error:
                    # History save failure does not affect main flow
                    print(f"\n⚠️  History save failed: {hist_error!s}")
            else:
                print("\n" + "=" * 70)
                print(f"❌ Question generation failed: {result.get('error', 'Unknown error')}")
                if result.get("reason"):
                    print(f"Reason: {result['reason']}")
                print("=" * 70)

        except Exception as e:
            print("\n" + "=" * 70)
            print(f"❌ Question generation failed: {e!s}")
            import traceback

            print("\nDebug information:")
            print(traceback.format_exc())
            print("=" * 70)

    async def run_research_mode(self):
        """Run deep research mode"""
        print("\n" + "=" * 70)
        print("🔬 Deep Research System")
        print("=" * 70)

        # Select knowledge base
        kb_name = self.select_kb(default="ai_textbook")
        print(f"✅ Selected knowledge base: {kb_name}")

        # Input research topic
        print("\n" + "-" * 70)
        print("Please enter research topic:")
        print("-" * 70)
        topic = input().strip()

        if not topic:
            print("❌ No topic entered, returning to main menu")
            return

        # Select research mode
        print("\n" + "-" * 70)
        print("🎯 Research mode:")
        print("-" * 70)
        print("1. Quick - 2 subtopics, 2 iterations")
        print("2. Standard - 5 subtopics, 5 iterations")
        print("3. Deep - 8 subtopics, 7 iterations")
        print("4. Auto - Automatically generate subtopic count")
        print("-" * 70)

        preset_map = {"1": "quick", "2": "standard", "3": "deep", "4": "auto"}
        while True:
            mode_choice = input("\nPlease select mode (1-4) [default: 1]: ").strip()
            if not mode_choice:
                preset = "quick"
                break
            if mode_choice in preset_map:
                preset = preset_map[mode_choice]
                break
            print("❌ Invalid option, please try again")

        print("\n" + "=" * 70)
        print("🚀 Starting deep research...")
        print("=" * 70)

        try:
            # Import research pipeline
            from src.agents.research.research_pipeline import ResearchPipeline
            from src.services.config import load_config_with_main

            # Load configuration using unified config loader
            config = load_config_with_main("main.yaml", project_root)

            # Extract research.* configs to top level (ResearchPipeline expects flat structure)
            research_config = config.get("research", {})
            if "planning" not in config:
                config["planning"] = research_config.get("planning", {}).copy()
            if "researching" not in config:
                config["researching"] = research_config.get("researching", {}).copy()
            if "reporting" not in config:
                config["reporting"] = research_config.get("reporting", {}).copy()
            if "rag" not in config:
                config["rag"] = research_config.get("rag", {}).copy()
            if "queue" not in config:
                config["queue"] = research_config.get("queue", {}).copy()
            if "presets" not in config:
                config["presets"] = research_config.get("presets", {}).copy()

            # Set output paths
            if "system" not in config:
                config["system"] = {}
            output_base = project_root / "data" / "user" / "research"
            config["system"]["output_base_dir"] = str(output_base / "cache")
            config["system"]["reports_dir"] = str(output_base / "reports")

            # Apply preset mode configuration
            preset_configs = {
                "quick": {
                    "planning": {"decompose": {"initial_subtopics": 2, "mode": "manual"}},
                    "researching": {"max_iterations": 2},
                },
                "standard": {
                    "planning": {"decompose": {"initial_subtopics": 5, "mode": "manual"}},
                    "researching": {"max_iterations": 5},
                },
                "deep": {
                    "planning": {"decompose": {"initial_subtopics": 8, "mode": "manual"}},
                    "researching": {"max_iterations": 7},
                },
                "auto": {
                    "planning": {"decompose": {"mode": "auto", "auto_max_subtopics": 8}},
                    "researching": {"max_iterations": 6},
                },
            }

            if preset in preset_configs:
                preset_cfg = preset_configs[preset]
                # Apply planning configuration
                if "planning" in preset_cfg:
                    for key, value in preset_cfg["planning"].items():
                        if key not in config["planning"]:
                            config["planning"][key] = {}
                        config["planning"][key].update(value)
                # Apply researching configuration
                if "researching" in preset_cfg:
                    config["researching"].update(preset_cfg["researching"])

                if preset == "auto":
                    print(
                        f"✅ Auto mode enabled (automatically generate subtopic count, max: {config['planning']['decompose'].get('auto_max_subtopics', 8)})"
                    )
                else:
                    print(f"✅ {preset.capitalize()} mode enabled")

            # Create research pipeline
            pipeline = ResearchPipeline(
                config=config, api_key=self.api_key, base_url=self.base_url, kb_name=kb_name
            )

            # Execute research
            result = await pipeline.run(topic)

            print("\n" + "=" * 70)
            print("✅ Research completed!")
            print("=" * 70)
            print(f"📁 Report location: {result['final_report_path']}")
            print(f"📊 Research ID: {result['research_id']}")

            metadata = result.get("metadata", {})
            if metadata:
                print("\n📈 Research statistics:")
                print(f"   Report word count: {metadata.get('report_word_count', 0)}")
                stats = metadata.get("statistics", {})
                if stats:
                    print(f"   Topic blocks: {stats.get('total_blocks', 0)}")
                    print(f"   Completed topics: {stats.get('completed', 0)}")
                    print(f"   Tool calls: {stats.get('total_tool_calls', 0)}")

            print("=" * 70)

            # Save to history
            try:
                # Read report content
                report_content = ""
                if result.get("final_report_path") and Path(result["final_report_path"]).exists():
                    with open(result["final_report_path"], encoding="utf-8") as f:
                        report_content = f.read()

                history_manager.add_entry(
                    activity_type=ActivityType.RESEARCH,
                    title=topic,
                    content={
                        "topic": topic,
                        "report": report_content,
                        "report_path": result.get("final_report_path", ""),
                        "research_id": result.get("research_id", ""),
                        "kb_name": kb_name,
                        "metadata": metadata,
                    },
                    summary=(
                        report_content[:200] + "..."
                        if len(report_content) > 200
                        else report_content
                    ),
                )
            except Exception as hist_error:
                # History save failure does not affect main flow
                logger.warning(f"History save failed: {hist_error!s}")

        except Exception as e:
            logger.section("Research failed")
            logger.error(str(e))
            import traceback

            logger.debug("Debug information:")
            logger.debug(traceback.format_exc())

    async def run_ideagen_mode(self):
        """Run idea generation mode"""
        print("\n" + "=" * 70)
        print("💡 Idea Generation System")
        print("=" * 70)

        # Select knowledge base
        kb_name = self.select_kb()
        print(f"✅ Selected knowledge base: {kb_name}")

        # Input materials
        print("\n" + "-" * 70)
        print(
            "Please enter knowledge points or material content (multi-line input supported, empty line to finish):"
        )
        print("-" * 70)

        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)

        if not lines:
            print("❌ No content entered, returning to main menu")
            return

        materials = "\n".join(lines)

        print("\n" + "=" * 70)
        print("🚀 Starting research idea generation...")
        print("=" * 70)

        try:
            # Import ideagen module
            from src.agents.ideagen.idea_generation_workflow import IdeaGenerationWorkflow
            from src.agents.ideagen.material_organizer_agent import MaterialOrganizerAgent

            # Organize materials
            organizer = MaterialOrganizerAgent(api_key=self.api_key, base_url=self.base_url)

            print("📊 Extracting knowledge points...")
            knowledge_points = await organizer.extract_knowledge_points(materials)
            print(f"✅ Extracted {len(knowledge_points)} knowledge points")

            if not knowledge_points:
                print("❌ Failed to extract valid knowledge points")
                return

            # Generate ideas
            workflow = IdeaGenerationWorkflow(api_key=self.api_key, base_url=self.base_url)

            print("🔍 Generating research ideas...")
            result = await workflow.process(knowledge_points)

            print("\n" + "=" * 70)
            print("✅ Research idea generation completed!")
            print("=" * 70)
            print(result)
            print("=" * 70)

        except Exception as e:
            logger.section("Generation failed")
            logger.error(str(e))
            import traceback

            logger.debug("Debug information:")
            logger.debug(traceback.format_exc())

    def run_web_mode(self):
        """Start web service"""
        print("\n" + "=" * 70)
        print("🌐 Start Web Service")
        print("=" * 70)
        print("1. Start backend API only (port 8000)")
        print("2. Start frontend only (port 3000)")
        print("3. Start both frontend and backend")
        print("4. Return to main menu")
        print("=" * 70)

        while True:
            choice = input("\nPlease select (1-4): ").strip()
            if choice == "1":
                print("\n🚀 Starting backend service...")
                print("Command: python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload")
                print("-" * 70)
                import subprocess

                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "api.main:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                        "--reload",
                    ],
                    check=False,
                )
                break
            if choice == "2":
                print("\n🚀 Starting frontend service...")
                print("Command: cd web && npm run dev")
                print("-" * 70)
                import subprocess

                web_dir = Path(__file__).parent / "web"
                subprocess.run(["npm", "run", "dev"], check=False, cwd=web_dir)
                break
            if choice == "3":
                print("\n🚀 Starting both frontend and backend services...")
                print("Command: python start_web.py")
                print("-" * 70)
                import subprocess

                subprocess.run([sys.executable, "start_web.py"], check=False)
                break
            if choice == "4":
                return
            print("❌ Invalid option, please try again")

    def show_settings(self):
        """Display settings"""
        print("\n" + "=" * 70)
        print("⚙️  System Settings")
        print("=" * 70)

        # Display LLM configuration
        try:
            llm_config = get_llm_config()
            print("\n📦 LLM Configuration:")
            print(f"   Model: {llm_config.model or 'N/A'}")
            print(f"   API Endpoint: {llm_config.base_url or 'N/A'}")
            print(f"   API Key: {'Configured' if llm_config.api_key else 'Not configured'}")
        except Exception as e:
            print(f"   ❌ Load failed: {e}")

        # Display knowledge bases
        print("\n📚 Available knowledge bases:")
        for i, kb in enumerate(self.available_kbs, 1):
            print(f"   {i}. {kb}")

        # Display configuration file locations
        print("\n📁 Configuration file locations:")
        env_files = [".env", "DeepTutor.env"]
        for env_file in env_files:
            env_path = Path(__file__).parent / env_file
            if env_path.exists():
                print(f"   ✅ {env_path}")
            else:
                print(f"   ⚪ {env_path} (not found)")

        print("\n" + "=" * 70)
        print(
            "💡 Tip: To modify settings, edit the .env file directly, or use the Settings page in the Web interface"
        )
        print("=" * 70)

        input("\nPress Enter to return to main menu...")

    async def run(self):
        """Run main loop"""
        while True:
            try:
                choice = self.show_main_menu()

                if choice == "1":
                    await self.run_solve_mode()
                elif choice == "2":
                    await self.run_question_mode()
                elif choice == "3":
                    await self.run_research_mode()
                elif choice == "4":
                    await self.run_ideagen_mode()
                elif choice == "5":
                    self.run_web_mode()
                    continue  # Don't ask to continue after web mode
                elif choice == "6":
                    self.show_settings()
                    continue  # Don't ask to continue after settings
                elif choice == "7":
                    print("\n" + "=" * 70)
                    print("👋 Thank you for using DeepTutor Intelligent Teaching Assistant System!")
                    print("=" * 70)
                    break

                # Ask if continue
                print("\n" + "-" * 70)
                continue_choice = input("Continue using? (y/n) [default: y]: ").strip().lower()
                if continue_choice == "n":
                    print("\n" + "=" * 70)
                    print("👋 Thank you for using DeepTutor Intelligent Teaching Assistant System!")
                    print("=" * 70)
                    break

            except KeyboardInterrupt:
                print("\n\n" + "=" * 70)
                print("👋 Program interrupted, thank you for using!")
                print("=" * 70)
                break
            except Exception as e:
                print(f"\n❌ Error occurred: {e!s}")
                print("Please retry or exit the program")


def main():
    """Main function"""
    try:
        starter = AITutorStarter()
        asyncio.run(starter.run())
    except Exception as e:
        logger.error(f"Startup failed: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    # Initialize user data directories
    try:
        from src.services.setup import init_user_directories

        init_user_directories(project_root)
    except Exception as e:
        logger.warning(f"Failed to initialize user directories: {e}")
        logger.info("Continuing anyway...")

    main()
