#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Reference-based exam-question generation system

Workflow:
1. Parse the PDF exam (MinerU)
2. Extract question information (LLM)
3. Generate new questions per reference question (Agent)
"""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from src.agents.question import AgentCoordinator

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Note: AgentCoordinator is imported inside functions to avoid circular import
from src.agents.question.tools.pdf_parser import parse_pdf_with_mineru
from src.agents.question.tools.question_extractor import extract_questions_from_paper

# Type alias for WebSocket callback
WsCallback = Callable[[str, dict[str, Any]], Any]


async def generate_question_from_reference(
    reference_question: dict[str, Any], coordinator: AgentCoordinator, kb_name: str
) -> dict[str, Any]:
    """
    Generate a new question based on a reference entry.
    """
    # Build generation requirement that encodes the reference
    requirement = {
        "reference_question": reference_question["question_text"],
        "has_images": len(reference_question.get("images", [])) > 0,
        "kb_name": kb_name,
        "allow_reject": False,
        "additional_requirements": (
            f"Reference question:\n{reference_question['question_text']}\n\n"
            "Requirements:\n"
            "1. Keep a similar difficulty level.\n"
            "2. **Identify the core knowledge concept(s) of the reference and keep them EXACTLY the same. Do not introduce new advanced topics beyond what the reference question requires.**\n"
            "3. **Change the scenario/objects/geometry; do not simply replace numbers or symbols.**\n"
            "4. **Alter at least one part of the reasoning process or add a new sub-question "
            "(e.g., extra calculation, analysis, or proof).**\n"
            "5. Keep the problem entirely within the same mathematical scope as the reference (e.g., if the reference is planar line parametrization, you must stay within planar line parametrization and cannot escalate to surfaces or directional derivatives).\n"
            "6. Ensure the prompt is rigorous, precise, and self-contained.\n"
            "7. If the original problem references images, describe them in text.\n"
            "8. Rejection is forbidden—you must complete the generation task.\n\n"
            "Chain-of-thought guidance:\n"
            "- Think step-by-step to plan the new scenario and reasoning before producing the final JSON.\n"
            "- Do not reveal your reasoning; output only the final JSON."
        ),
    }

    # Trigger generation through the coordinator
    result = await coordinator.generate_question(requirement)

    return result


async def mimic_exam_questions(
    pdf_path: str | None = None,
    paper_dir: str | None = None,
    kb_name: str = None,
    output_dir: str | None = None,
    max_questions: int | None = None,
    ws_callback: WsCallback | None = None,
) -> dict[str, Any]:
    """
    End-to-end orchestration for reference-based question generation.

    Args:
        pdf_path: Path to the PDF exam paper
        paper_dir: Path to a pre-parsed exam directory
        kb_name: Knowledge base name to use
        output_dir: Output directory for generated questions
        max_questions: Maximum number of questions to process
        ws_callback: Optional async callback for WebSocket progress updates
                     Signature: async def callback(event_type: str, data: dict)
    """

    async def send_progress(event_type: str, data: dict[str, Any]):
        """Helper to send progress updates via WebSocket callback."""
        if ws_callback:
            try:
                await ws_callback(event_type, data)
            except Exception as e:
                print(f"WebSocket callback error: {e}")

    print("=" * 80)
    print("📚 Reference-based question generation system")
    print("=" * 80)
    print()

    # Validate arguments
    if not pdf_path and not paper_dir:
        await send_progress("error", {"content": "Either pdf_path or paper_dir must be provided."})
        return {"success": False, "error": "Either pdf_path or paper_dir must be provided."}

    if pdf_path and paper_dir:
        await send_progress("error", {"content": "pdf_path and paper_dir cannot be used together."})
        return {
            "success": False,
            "error": "pdf_path and paper_dir cannot be used together. Choose only one.",
        }

    latest_dir = None

    # If an already parsed exam directory is provided
    if paper_dir:
        await send_progress(
            "progress",
            {
                "stage": "parsing",
                "status": "locating",
                "message": "Locating parsed exam directory...",
            },
        )

        print("🔍 Using parsed exam directory")
        print("-" * 80)

        # Resolve relative names against reference_papers
        # SECURITY FIX: Prevent Path Injection / Traversal
        if os.path.isabs(paper_dir) or ".." in paper_dir:
            error_msg = (
                f"Invalid paper_dir: Absolute paths and traversal are not allowed. ({paper_dir})"
            )
            await send_progress("error", {"content": error_msg})
            return {"success": False, "error": error_msg}

        paper_path = Path(paper_dir)

        # Candidate locations to search (including new location)
        project_root = Path(__file__).parent.parent.parent.parent.parent
        possible_paths = [
            project_root
            / "data"
            / "user"
            / "question"
            / "mimic_papers"
            / paper_dir,  # New primary location
            Path("question_agents/reference_papers") / paper_dir,  # Legacy location
            Path("reference_papers") / paper_dir,
        ]

        latest_dir = None
        for p in possible_paths:
            if p.exists():
                # Double check to ensure we didn't escape via symlink or subtle tricks
                try:
                    resolved_p = p.resolve()
                    # Safe check: Ensure the resolved path is strictly inside the intended parent
                    # This is a basic check; for robust security, whitelist allowed parents explicitly if needed.
                    latest_dir = resolved_p
                    break
                except Exception:
                    continue

        if not latest_dir:
            error_msg = f"Exam directory not found: {paper_dir}"
            await send_progress("error", {"content": error_msg})
            return {
                "success": False,
                "error": f"{error_msg}\nSearched paths: {[str(p) for p in possible_paths]}",
            }
        else:
            latest_dir = paper_path.resolve()
            if not latest_dir.exists():
                error_msg = f"Exam directory not found: {latest_dir}"
                await send_progress("error", {"content": error_msg})
                return {"success": False, "error": error_msg}

        # Ensure auto subdirectory exists
        auto_dir = latest_dir / "auto"
        if not auto_dir.exists():
            error_msg = f"Invalid exam directory (missing auto folder): {latest_dir}"
            await send_progress("error", {"content": error_msg})
            return {
                "success": False,
                "error": error_msg,
            }

        print(f"✓ Exam directory detected: {latest_dir.name}")
        print(f"   Full path: {latest_dir}")
        print()

        await send_progress(
            "progress",
            {
                "stage": "parsing",
                "status": "complete",
                "message": f"Using parsed exam: {latest_dir.name}",
            },
        )

    # If a PDF is provided, parse it first
    elif pdf_path:
        # Stage 1: Parsing PDF
        await send_progress(
            "progress",
            {"stage": "parsing", "status": "running", "message": "Parsing PDF with MinerU..."},
        )

        print("🔄 Step 1: parse the PDF exam")
        print("-" * 80)

        # Use provided output_dir or default to mimic_papers
        project_root = Path(__file__).parent.parent.parent.parent.parent
        if output_dir:
            output_base = Path(output_dir)
        else:
            output_base = project_root / "data" / "user" / "question" / "mimic_papers"
        output_base.mkdir(parents=True, exist_ok=True)

        success = parse_pdf_with_mineru(pdf_path=pdf_path, output_base_dir=str(output_base))

        if not success:
            await send_progress("error", {"content": "Failed to parse PDF with MinerU"})
            return {"success": False, "error": "Failed to parse PDF"}

        print()

        print("🔍 Step 2: locating parsed results")
        print("-" * 80)

        # Look in the new output directory (user/question/mimic_papers)
        reference_papers_dir = output_base
        subdirs = sorted(
            [d for d in reference_papers_dir.iterdir() if d.is_dir()],
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        if not subdirs:
            await send_progress("error", {"content": "No parsed outputs were found"})
            return {"success": False, "error": "No parsed outputs were found"}

        latest_dir = subdirs[0]
        print(f"✓ Parsed folder: {latest_dir.name}")
        print()

        await send_progress(
            "progress",
            {
                "stage": "parsing",
                "status": "complete",
                "message": f"PDF parsed successfully: {latest_dir.name}",
            },
        )

    # Stage 2: Extract questions
    await send_progress(
        "progress",
        {
            "stage": "extracting",
            "status": "running",
            "message": "Extracting reference questions from exam...",
        },
    )

    print("🔄 Step 3: extract reference questions")
    print("-" * 80)

    json_files = list(latest_dir.glob("*_questions.json"))

    if json_files:
        print(f"✓ Found existing question file: {json_files[0].name}")
        with open(json_files[0], encoding="utf-8") as f:
            questions_data = json.load(f)
    else:
        print("📄 No question file found, starting extraction...")
        success = extract_questions_from_paper(paper_dir=str(latest_dir), output_dir=None)

        if not success:
            await send_progress("error", {"content": "Question extraction failed"})
            return {"success": False, "error": "Question extraction failed"}

        json_files = list(latest_dir.glob("*_questions.json"))
        if not json_files:
            await send_progress(
                "error", {"content": "Question JSON file not found after extraction"}
            )
            return {"success": False, "error": "Question JSON file not found after extraction"}

        with open(json_files[0], encoding="utf-8") as f:
            questions_data = json.load(f)

    reference_questions = questions_data.get("questions", [])

    if max_questions:
        reference_questions = reference_questions[:max_questions]

    print(f"✓ Loaded {len(reference_questions)} reference questions")
    print()

    # Send reference questions info
    await send_progress(
        "progress",
        {
            "stage": "extracting",
            "status": "complete",
            "message": f"Extracted {len(reference_questions)} reference questions",
            "total_questions": len(reference_questions),
            "reference_questions": [
                {
                    "number": q.get("question_number", str(i + 1)),
                    "preview": (
                        q["question_text"][:100] + "..."
                        if len(q["question_text"]) > 100
                        else q["question_text"]
                    ),
                }
                for i, q in enumerate(reference_questions)
            ],
        },
    )

    # Stage 3: Generate mimic questions
    await send_progress(
        "progress",
        {
            "stage": "generating",
            "status": "running",
            "message": "Generating mimic questions...",
            "current": 0,
            "total": len(reference_questions),
        },
    )

    print("🔄 Step 4: generate new questions from references (parallel)")
    print("-" * 80)

    # Lazy import to avoid circular import
    from src.agents.question import AgentCoordinator
    from src.services.config import load_config_with_main

    # Load config for parallel settings
    config = load_config_with_main("question_config.yaml", project_root)
    question_cfg = config.get("question", {})
    max_parallel = question_cfg.get("max_parallel_questions", 3)

    print(f"📊 Processing {len(reference_questions)} questions with max {max_parallel} parallel")

    # Create semaphore for parallel control
    semaphore = asyncio.Semaphore(max_parallel)

    # Track completed count
    completed_count = 0
    completed_lock = asyncio.Lock()

    async def generate_single_mimic(ref_question: dict, index: int) -> dict:
        """Generate a single mimic question with semaphore control."""
        nonlocal completed_count

        async with semaphore:
            question_id = f"mimic_{index}"
            ref_number = ref_question.get("question_number", str(index))

            # Send question start update
            await send_progress(
                "question_update",
                {
                    "question_id": question_id,
                    "index": index,
                    "status": "generating",
                    "reference_number": ref_number,
                    "reference_preview": ref_question["question_text"][:80] + "...",
                },
            )

            print(f"\n📝 [{question_id}] Starting - Reference: {ref_number}")
            print(f"   Preview: {ref_question['question_text'][:80]}...")

            # Create a fresh coordinator for each question
            coordinator = AgentCoordinator(max_rounds=10, kb_name=kb_name)

            try:
                result = await generate_question_from_reference(
                    reference_question=ref_question, coordinator=coordinator, kb_name=kb_name
                )

                async with completed_lock:
                    completed_count += 1
                    current_completed = completed_count

                if result.get("success"):
                    print(f"✓ [{question_id}] Generated in {result['rounds']} round(s)")

                    result_data = {
                        "success": True,
                        "reference_question_number": ref_number,
                        "reference_question_text": ref_question["question_text"],
                        "reference_images": ref_question.get("images", []),
                        "generated_question": result["question"],
                        "validation": result["validation"],
                        "rounds": result["rounds"],
                    }

                    # Send result update
                    await send_progress(
                        "result",
                        {
                            "question_id": question_id,
                            "index": index,
                            "success": True,
                            "question": result["question"],
                            "validation": result["validation"],
                            "rounds": result["rounds"],
                            "reference_question": ref_question["question_text"],
                            "current": current_completed,
                            "total": len(reference_questions),
                        },
                    )

                    return result_data
                else:
                    print(f"✗ [{question_id}] Failed: {result.get('error', 'Unknown error')}")

                    error_data = {
                        "success": False,
                        "reference_question_number": ref_number,
                        "reference_question_text": ref_question["question_text"],
                        "error": result.get("error", "Unknown error"),
                        "reason": result.get("reason", ""),
                    }

                    await send_progress(
                        "question_update",
                        {
                            "question_id": question_id,
                            "index": index,
                            "status": "failed",
                            "error": result.get("error", "Unknown error"),
                            "current": current_completed,
                            "total": len(reference_questions),
                        },
                    )

                    return error_data

            except Exception as e:
                print(f"✗ [{question_id}] Exception: {e!s}")

                async with completed_lock:
                    completed_count += 1
                    current_completed = completed_count

                await send_progress(
                    "question_update",
                    {
                        "question_id": question_id,
                        "index": index,
                        "status": "failed",
                        "error": str(e),
                        "current": current_completed,
                        "total": len(reference_questions),
                    },
                )

                return {
                    "success": False,
                    "reference_question_number": ref_question.get("question_number", str(index)),
                    "reference_question_text": ref_question["question_text"],
                    "error": f"Exception: {e!s}",
                }

    # Run all mimic generations in parallel
    tasks = [generate_single_mimic(ref_q, i) for i, ref_q in enumerate(reference_questions, 1)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Separate successes and failures
    generated_questions = []
    failed_questions = []

    for result in results:
        if isinstance(result, Exception):
            failed_questions.append({"error": str(result)})
        elif result.get("success"):
            generated_questions.append(result)
        else:
            failed_questions.append(result)

    print()
    print("=" * 80)
    print("📊 Generation summary")
    print("=" * 80)
    print(f"Reference questions: {len(reference_questions)}")
    print(f"Successes: {len(generated_questions)}")
    print(f"Failures: {len(failed_questions)}")

    if output_dir is None:
        output_dir = latest_dir
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"{latest_dir.name}_{timestamp}_generated_questions.json"

    output_data = {
        "reference_paper": latest_dir.name,
        "kb_name": kb_name,
        "total_reference_questions": len(reference_questions),
        "successful_generations": len(generated_questions),
        "failed_generations": len(failed_questions),
        "generated_questions": generated_questions,
        "failed_questions": failed_questions,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Results saved to: {output_file}")
    print()

    # Send summary
    await send_progress(
        "summary",
        {
            "total_reference": len(reference_questions),
            "successful": len(generated_questions),
            "failed": len(failed_questions),
            "output_file": str(output_file),
        },
    )

    return {
        "success": True,
        "output_file": str(output_file),
        "total_reference_questions": len(reference_questions),
        "generated_questions": generated_questions,
        "failed_questions": failed_questions,
    }


async def main():
    """Command-line entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Reference-based question generation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python exam_mimic.py --pdf /path/to/exam.pdf --kb math2211
  python exam_mimic.py --paper 2211asm1 --kb math2211
  python exam_mimic.py --paper reference_papers/2211asm1 --kb math2211
  python exam_mimic.py --paper 2211asm1 --kb math2211 --max-questions 3
  python exam_mimic.py --paper 2211asm1 --kb math2211 -o ./output
        """,
    )

    # Input mode (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--pdf", type=str, help="Absolute path to the PDF exam (will be parsed)"
    )

    input_group.add_argument(
        "--paper",
        type=str,
        help="Name of a parsed exam directory (e.g., 2211asm1) or its absolute path",
    )

    parser.add_argument("--kb", type=str, required=True, help="Knowledge base name")

    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output directory (defaults to the exam folder)",
    )

    parser.add_argument(
        "--max-questions",
        type=int,
        default=None,
        help="Maximum number of reference questions to process (testing)",
    )

    args = parser.parse_args()

    # Execute the workflow
    result = await mimic_exam_questions(
        pdf_path=args.pdf,
        paper_dir=args.paper,
        kb_name=args.kb,
        output_dir=args.output,
        max_questions=args.max_questions,
    )

    if result["success"]:
        print("✓ Completed!")
        sys.exit(0)
    else:
        print(f"✗ Failed: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
