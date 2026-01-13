#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extract question information from MinerU-parsed exam papers

This script reads MinerU-parsed markdown files and content_list.json,
uses LLM to analyze and extract all questions, including question content and related images.
"""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from typing import Any

project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from openai import OpenAI

from src.services.config import get_agent_params
from src.services.llm import get_llm_config


def load_parsed_paper(paper_dir: Path) -> tuple[str | None, list[dict] | None, Path]:
    """
    Load MinerU-parsed exam paper files

    Args:
        paper_dir: MinerU output directory (e.g., reference_papers/paper_name_20241129/)

    Returns:
        (markdown_content, content_list, images_dir)
    """
    auto_dir = paper_dir / "auto"
    if not auto_dir.exists():
        auto_dir = paper_dir

    md_files = list(auto_dir.glob("*.md"))
    if not md_files:
        print(f"✗ Error: No markdown file found in {auto_dir}")
        return None, None, auto_dir / "images"

    md_file = md_files[0]
    print(f"📄 Found markdown file: {md_file.name}")

    with open(md_file, encoding="utf-8") as f:
        markdown_content = f.read()

    json_files = list(auto_dir.glob("*_content_list.json"))
    content_list = None
    if json_files:
        json_file = json_files[0]
        print(f"📋 Found content_list file: {json_file.name}")
        with open(json_file, encoding="utf-8") as f:
            content_list = json.load(f)
    else:
        print("⚠️ Warning: content_list.json file not found, will use markdown content only")

    images_dir = auto_dir / "images"
    if images_dir.exists():
        image_count = len(list(images_dir.glob("*")))
        print(f"🖼️ Found image directory: {image_count} images")
    else:
        print("⚠️ Warning: images directory not found")

    return markdown_content, content_list, images_dir


def extract_questions_with_llm(
    markdown_content: str,
    content_list: list[dict] | None,
    images_dir: Path,
    api_key: str,
    base_url: str,
    model: str,
) -> list[dict[str, Any]]:
    """
    Use LLM to analyze markdown content and extract questions

    Args:
        markdown_content: Document content in Markdown format
        content_list: MinerU-generated content_list (optional)
        images_dir: Image directory path
        api_key: OpenAI API key
        base_url: API endpoint URL
        model: Model name

        Returns:
        Question list, each question contains:
        {
            "question_number": Question number,
            "question_text": Question text content (multiple choice includes options),
            "images": [List of relative paths to related images]
        }
    """
    client = OpenAI(api_key=api_key, base_url=base_url)

    image_list = []
    if images_dir.exists():
        for img_file in sorted(images_dir.glob("*")):
            if img_file.suffix.lower() in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
                image_list.append(img_file.name)

    system_prompt = """You are a professional exam paper analysis assistant. Your task is to extract all question information from the provided exam paper content.

Please carefully analyze the exam paper content and extract the following information for each question:
1. Question number (e.g., "1.", "Question 1", etc.)
2. Complete question text content (if multiple choice, include all options)
3. Related image file names (if the question references images)

For multiple choice questions, please merge the stem and all options into one complete question text, for example:
"1. Which of the following descriptions about neural networks is correct? ()\nA. Option A content\nB. Option B content\nC. Option C content\nD. Option D content"

Please return results in JSON format as follows:
```json
{
    "questions": [
        {
            "question_number": "1",
            "question_text": "Complete question content (including options)...",
            "images": ["image_001.jpg", "image_002.jpg"]
        },
        {
            "question_number": "2",
            "question_text": "Complete content of another question...",
            "images": []
        }
    ]
}
```

Important Notes:
1. Ensure all questions are extracted, do not miss any
2. Keep the original question text, do not modify or summarize
3. For multiple choice questions, must merge stem and options in question_text
4. If a question has no associated images, set images field to empty array []
5. Image file names should be actual existing file names
6. Ensure the returned format is valid JSON
"""

    user_prompt = f"""Exam paper content (Markdown format):

{markdown_content[:15000]}

Available image files:
{json.dumps(image_list, ensure_ascii=False, indent=2)}

Please analyze the above exam paper content, extract all question information, and return in JSON format.
"""

    print("\n🤖 Using LLM to analyze questions...")
    print(f"📊 Model: {model}")
    print(f"📝 Document length: {len(markdown_content)} characters")
    print(f"🖼️ Available images: {len(image_list)}")

    # Get agent parameters from unified config
    agent_params = get_agent_params("question")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=agent_params["temperature"],
            max_tokens=agent_params["max_tokens"],
            response_format={"type": "json_object"},
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        questions = result.get("questions", [])
        print(f"✓ Successfully extracted {len(questions)} questions")

        return questions

    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing error: {e!s}")
        print(f"LLM response content: {result_text[:500]}...")
        return []
    except Exception as e:
        print(f"✗ LLM call failed: {e!s}")
        import traceback

        traceback.print_exc()
        return []


def save_questions_json(questions: list[dict[str, Any]], output_dir: Path, paper_name: str) -> Path:
    """
    Save question information as JSON file

    Args:
        questions: Question list
        output_dir: Output directory
        paper_name: Paper name

    Returns:
        Saved file path
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    output_data = {
        "paper_name": paper_name,
        "extraction_time": datetime.now().isoformat(),
        "total_questions": len(questions),
        "questions": questions,
    }

    output_file = output_dir / f"{paper_name}_{timestamp}_questions.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"💾 Question information saved to: {output_file.name}")

    print("\n📋 Question statistics:")
    print(f"  Total questions: {len(questions)}")

    questions_with_images = sum(1 for q in questions if q.get("images"))
    print(f"  Questions with images: {questions_with_images}")

    return output_file


def extract_questions_from_paper(paper_dir: str, output_dir: str | None = None) -> bool:
    """
    Extract questions from parsed exam paper

    Args:
        paper_dir: MinerU-parsed directory path
        output_dir: Output directory (default: paper_dir)

    Returns:
        Whether extraction was successful
    """
    paper_dir = Path(paper_dir).resolve()
    if not paper_dir.exists():
        print(f"✗ Error: Directory does not exist: {paper_dir}")
        return False

    print(f"📁 Paper directory: {paper_dir}")

    markdown_content, content_list, images_dir = load_parsed_paper(paper_dir)

    if not markdown_content:
        print("✗ Error: Unable to load paper content")
        return False

    try:
        llm_config = get_llm_config()
    except ValueError as e:
        print(f"✗ {e!s}")
        print(
            "Tip: Please create .env file in project root and configure LLM-related environment variables"
        )
        return False

    questions = extract_questions_with_llm(
        markdown_content=markdown_content,
        content_list=content_list,
        images_dir=images_dir,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        model=llm_config.model,
    )

    if not questions:
        print("⚠️ Warning: No questions extracted")
        return False

    if output_dir is None:
        output_dir = paper_dir
    else:
        output_dir = Path(output_dir)

    paper_name = paper_dir.name
    output_file = save_questions_json(questions, output_dir, paper_name)

    print("\n✓ Question extraction completed!")
    print(f"📄 View results: {output_file}")

    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Extract question information from MinerU-parsed exam papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract questions from parsed exam paper directory
  python question_extractor.py reference_papers/exam_20241129_143052

  # Specify output directory
  python question_extractor.py reference_papers/exam_20241129_143052 -o ./output
        """,
    )

    parser.add_argument("paper_dir", type=str, help="MinerU-parsed exam paper directory path")

    parser.add_argument(
        "-o", "--output", type=str, default=None, help="Output directory (default: paper directory)"
    )

    args = parser.parse_args()

    success = extract_questions_from_paper(args.paper_dir, args.output)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
