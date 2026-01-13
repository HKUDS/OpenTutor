#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Query Numbered Item Tool - Query definitions, theorems, formulas, figures, etc.
"""

import json
from pathlib import Path
import sys

# Add parent directory to path (insert at front to prioritize project modules)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def query_numbered_item(
    identifier: str,
    kb_name: str | None = None,
    kb_base_dir: str | None = None,
    max_results: int | None = None,
) -> dict:
    """
    Query numbered item - Supports returning multiple matching results

    Args:
        identifier: Identifier of the numbered item
            - Definition/Theorem: e.g., "Definition 1.1", "Theorem 2.3"
            - Formula: e.g., "(1.2.1)", "(2.3.5)"
            - Figure: e.g., "Figure 1.1", "Figure 2.5"
            - Example: e.g., "Example 1.1", "Remark 2.1"
        kb_name: Knowledge base name (optional, defaults to default knowledge base)
        kb_base_dir: Knowledge base base directory (optional, defaults to knowledge_bases under project root)
        max_results: Maximum number of items to return (optional, defaults to config value or 5)

    Returns:
        dict: Dictionary containing query results
            {
                "identifier": str,  # Original query identifier
                "type": str,  # formula/definition/theorem/lemma/figure/example/remark
                "status": str,  # success/failed
                "count": int,  # Number of matched items
                "items": [  # List of all matched items (sorted by priority)
                    {
                        "identifier": str,  # Actual matched identifier
                        "type": str,
                        "content": str
                    },
                    ...
                ],
                "content": str,  # Backward compatible: single item content or merged content for multiple items
                "error": str (only when failed)
            }
    """
    # Load configuration for max_results if not specified
    if max_results is None:
        try:
            from src.services.config import load_config_with_main

            project_root = Path(__file__).parent.parent.parent
            config = load_config_with_main("main.yaml", project_root)
            max_results = config.get("tools", {}).get("query_item", {}).get("max_results", 5)
        except Exception:
            max_results = 5  # Default value

    # If path not specified, use absolute path relative to this file
    if kb_base_dir is None:
        # __file__ = DeepTutor/tools/query_item_tool.py
        # .parent = DeepTutor/tools
        # .parent = DeepTutor
        kb_base_dir = Path(__file__).parent.parent.parent / "data/knowledge_bases"
    else:
        kb_base_dir = Path(kb_base_dir)

    base_dir = kb_base_dir

    # Get knowledge base
    if not kb_name:
        config_file = base_dir / "kb_config.json"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = json.load(f)
                    kb_name = config.get("default")
            except Exception:
                pass

        if not kb_name:
            return {
                "identifier": identifier,
                "type": "unknown",
                "content": "",
                "status": "failed",
                "error": "Error: Knowledge base not specified and no default knowledge base",
            }

    # Load items
    kb_dir = base_dir / kb_name
    if not kb_dir.exists():
        return {
            "identifier": identifier,
            "type": "unknown",
            "content": "",
            "status": "failed",
            "error": f"Error: Knowledge base '{kb_name}' does not exist",
        }

    items_file = kb_dir / "numbered_items.json"
    if not items_file.exists():
        return {
            "identifier": identifier,
            "type": "unknown",
            "content": "",
            "status": "failed",
            "error": f"Error: numbered_items.json not found in knowledge base '{kb_name}'",
        }

    try:
        with open(items_file, encoding="utf-8") as f:
            raw_items = json.load(f)
    except Exception as e:
        return {
            "identifier": identifier,
            "type": "unknown",
            "content": "",
            "status": "failed",
            "error": f"Error: Unable to read file - {e}",
        }

    # Extract text content
    items = {}
    for key, value in raw_items.items():
        if isinstance(value, dict):
            items[key] = value.get("text", str(value))
        else:
            items[key] = value

    # Validate identifier parameter
    if not identifier:
        return {
            "identifier": identifier or "",
            "type": "unknown",
            "content": "",
            "status": "failed",
            "error": "Error: identifier parameter is empty or None",
        }

    # Ensure identifier is a string
    if not isinstance(identifier, str):
        identifier = str(identifier)

    # Determine type
    item_type = "unknown"
    identifier_lower = identifier.lower()
    if "figure" in identifier_lower:
        item_type = "figure"
    elif "definition" in identifier_lower:
        item_type = "definition"
    elif "theorem" in identifier_lower:
        item_type = "theorem"
    elif "lemma" in identifier_lower:
        item_type = "lemma"
    elif "example" in identifier_lower:
        item_type = "example"
    elif "remark" in identifier_lower:
        item_type = "remark"
    elif identifier.strip().startswith("(") and identifier.strip().endswith(")"):
        item_type = "formula"

    # 1. Exact match (highest priority)
    if identifier in items:
        matched_item = {"identifier": identifier, "type": item_type, "content": items[identifier]}
        return {
            "identifier": identifier,
            "type": item_type,
            "status": "success",
            "count": 1,
            "items": [matched_item],
            "content": items[identifier],  # Backward compatible
        }

    # 2. Case-insensitive exact match
    exact_matches = []
    for key, value in items.items():
        if key.lower() == identifier_lower:
            exact_matches.append({"identifier": key, "type": item_type, "content": value})

    if exact_matches:
        # Limit results
        if max_results and len(exact_matches) > max_results:
            exact_matches = exact_matches[:max_results]

        # Build content (backward compatible)
        content = (
            exact_matches[0]["content"]
            if len(exact_matches) == 1
            else "\n\n".join(
                [f"[{item['identifier']}]\n{item['content']}" for item in exact_matches]
            )
        )

        return {
            "identifier": identifier,
            "type": item_type,
            "status": "success",
            "count": len(exact_matches),
            "items": exact_matches,
            "content": content,
        }

    # 3. Prefix match (e.g., "2.1" matches "(2.1.1)", "(2.1.2)", etc.)
    prefix_matches = []
    identifier_clean = identifier.strip().strip("()")  # Remove parentheses, extract pure numbers

    for key, value in items.items():
        key_clean = key.strip().strip("()")
        # Prefix match: key starts with identifier (after removing parentheses)
        if (
            key_clean.startswith(identifier_clean + ".")
            or key_clean == identifier_clean
            or key.lower().startswith(identifier_lower)
        ):
            prefix_matches.append({"identifier": key, "type": item_type, "content": value})

    # Limit results
    if max_results and len(prefix_matches) > max_results:
        prefix_matches = prefix_matches[:max_results]

    if prefix_matches:
        # Build content
        content = (
            prefix_matches[0]["content"]
            if len(prefix_matches) == 1
            else "\n\n".join(
                [f"[{item['identifier']}]\n{item['content']}" for item in prefix_matches]
            )
        )

        return {
            "identifier": identifier,
            "type": item_type,
            "status": "success",
            "count": len(prefix_matches),
            "items": prefix_matches,
            "content": content,
        }

    # 4. Partial match (contains query string)
    partial_matches = []
    for key, value in items.items():
        if identifier_lower in key.lower():
            partial_matches.append({"identifier": key, "type": item_type, "content": value})

    # Limit results
    if max_results and len(partial_matches) > max_results:
        partial_matches = partial_matches[:max_results]

    if partial_matches:
        content = (
            partial_matches[0]["content"]
            if len(partial_matches) == 1
            else "\n\n".join(
                [f"[{item['identifier']}]\n{item['content']}" for item in partial_matches]
            )
        )

        return {
            "identifier": identifier,
            "type": item_type,
            "status": "success",
            "count": len(partial_matches),
            "items": partial_matches,
            "content": content,
        }

    # 5. Not found - provide suggestions
    suggestions = [k for k in items if identifier_lower in k.lower()][:5]
    error_msg = f"Numbered item '{identifier}' not found"
    if suggestions:
        error_msg += "\n\nSimilar items:\n" + "\n".join(f"  • {s}" for s in suggestions)

    return {
        "identifier": identifier,
        "type": item_type,
        "status": "failed",
        "count": 0,
        "items": [],
        "content": "",
        "error": error_msg,
    }


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        import io

        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    # Test
    print("Testing query_numbered_item\n" + "=" * 60)

    # Test 1
    print("\n[Test 1] Query formula (1.2.1):")
    result = query_numbered_item("(1.2.1)", kb_name="ai_textbook")
    print(f"Status: {result['status']}")
    print(f"Type: {result['type']}")
    print(f"Content: {result.get('content', result.get('error'))[:200]}...")

    print("\n" + "=" * 60)
