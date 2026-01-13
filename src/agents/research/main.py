#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DR-in-KG 2.0 - Main Entry
Deep research system based on dynamic topic queue

Usage:
  python main.py --topic "Research Topic" [--preset quick/standard/deep]
"""

import argparse
import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv
import yaml

from src.agents.research.research_pipeline import ResearchPipeline
from src.services.llm import get_llm_config


def load_config(config_path: str = None, preset: str = None) -> dict:
    """
    Load configuration file (with main.yaml merge)

    Args:
        config_path: Configuration file path (default: config/research_config.yaml)
        preset: Preset mode (quick/standard/deep)

    Returns:
        Configuration dictionary (merged with main.yaml)
    """
    if config_path is None:
        project_root = Path(__file__).parent.parent.parent.parent
        from src.services.config import load_config_with_main

        config = load_config_with_main("research_config.yaml", project_root)
    else:
        # If custom config path provided, load it directly (for backward compatibility)
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        with open(config_file, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

    # Apply preset
    if preset and "presets" in config and preset in config["presets"]:
        print(f"✓ Applied preset configuration: {preset}")
        preset_config = config["presets"][preset]
        for key, value in preset_config.items():
            if key in config and isinstance(value, dict):
                config[key].update(value)

    return config


def display_config(config: dict):
    """Display current configuration"""
    print("\n" + "=" * 70)
    print("📋 Current Configuration")
    print("=" * 70)

    planning = config.get("planning", {})
    researching = config.get("researching", {})
    reporting = config.get("reporting", {})

    print("【Planning Configuration】")
    print(f"  Initial subtopics: {planning.get('decompose', {}).get('initial_subtopics', 5)}")
    print(f"  Max subtopics: {planning.get('decompose', {}).get('max_subtopics', 10)}")

    print("\n【Researching Configuration】")
    print(f"  Max iterations: {researching.get('max_iterations', 5)}")
    print(f"  Research mode: {researching.get('research_mode', 'deep')}")
    print("  Enabled tools:")
    print(f"    - RAG: {researching.get('enable_rag_hybrid', True)}")
    print(f"    - Web Search: {researching.get('enable_web_search', True)}")
    print(f"    - Paper Search: {researching.get('enable_paper_search', True)}")

    print("\n【Reporting Configuration】")
    print(f"  Min section length: {reporting.get('min_section_length', 500)} characters")
    print(f"  Enable topic deduplication: {reporting.get('enable_deduplication', True)}")

    print("=" * 70 + "\n")


async def main():
    """Main function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="DR-in-KG 2.0 - Deep research system based on dynamic topic queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick mode
  python main.py --topic "Deep Learning Basics" --preset quick

  # Standard mode
  python main.py --topic "Transformer Architecture" --preset standard

  # Deep mode
  python main.py --topic "Graph Neural Networks" --preset deep
        """,
    )

    parser.add_argument("--topic", type=str, required=True, help="Research topic")

    parser.add_argument(
        "--config",
        type=str,
        default="config.yaml",
        help="Configuration file path (default: config.yaml)",
    )

    parser.add_argument(
        "--preset",
        type=str,
        choices=["quick", "standard", "deep"],
        help="Preset configuration (quick: fast, standard: standard, deep: deep)",
    )

    parser.add_argument("--output-dir", type=str, help="Output directory (overrides config file)")

    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Check API configuration
    try:
        llm_config = get_llm_config()
    except ValueError as e:
        print(f"✗ Error: {e}")
        print("Please configure in .env or DeepTutor.env file:")
        print("  LLM_MODEL=gpt-4o")
        print("  LLM_API_KEY=your_api_key_here")
        print("  LLM_HOST=https://api.openai.com/v1")
        sys.exit(1)

    # Load configuration
    try:
        config = load_config(args.config, args.preset)
    except Exception as e:
        print(f"✗ Failed to load configuration: {e!s}")
        sys.exit(1)

    # Override configuration (command line arguments take priority)
    if args.output_dir:
        config["system"]["output_base_dir"] = args.output_dir
        config["system"]["reports_dir"] = args.output_dir

    # Display configuration
    display_config(config)

    # Create research pipeline
    pipeline = ResearchPipeline(
        config=config, api_key=llm_config.api_key, base_url=llm_config.base_url
    )

    # Execute research
    try:
        result = await pipeline.run(topic=args.topic)

        print("\n" + "=" * 70)
        print("✓ Research completed!")
        print("=" * 70)
        print(f"Research ID: {result['research_id']}")
        print(f"Topic: {result['topic']}")
        print(f"Final Report: {result['final_report_path']}")
        print("=" * 70 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Research interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n✗ Research failed: {e!s}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Windows compatibility
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
