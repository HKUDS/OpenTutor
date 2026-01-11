"""Web Search Utilities"""

from datetime import datetime
import json
import os
from typing import Any


def save_results(result: dict[str, Any], output_dir: str, provider: str) -> str:
    """Save search results to a JSON file."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"search_{provider}_{timestamp}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return output_path
