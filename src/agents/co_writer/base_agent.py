#!/usr/bin/env python
"""
BaseCoWriterAgent - Base class for co_writer module agents.

This provides a unified base class for co_writer agents that want to use
the new unified BaseAgent architecture.

Note: Existing EditAgent and NarratorAgent have not been migrated to inherit
from this class as they have specialized initialization and business logic.
New co_writer agents should consider using this base class.
"""

from pathlib import Path
import sys
from typing import Any

# Add project root to path
_project_root = Path(__file__).parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import the unified BaseAgent
from src.agents.base_agent import BaseAgent as UnifiedBaseAgent


class BaseCoWriterAgent(UnifiedBaseAgent):
    """
    Base class for Co-Writer module agents.

    This class provides a unified interface for co_writer agents,
    wrapping the new unified BaseAgent with co_writer-specific defaults.
    """

    def __init__(
        self,
        agent_name: str = "co_writer_agent",
        language: str = "en",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        Initialize base Agent.

        Args:
            agent_name: Agent name
            language: Language setting ('zh' | 'en')
            api_key: API key (optional, defaults to environment)
            base_url: API endpoint (optional, defaults to environment)
        """
        # Call unified BaseAgent init
        super().__init__(
            module_name="co_writer",
            agent_name=agent_name,
            api_key=api_key,
            base_url=base_url,
            language=language,
        )

    async def process(self, *args, **kwargs) -> Any:
        """
        Main processing logic.

        Subclasses should override this method.
        """
        raise NotImplementedError("Subclasses must implement process()")


__all__ = ["BaseCoWriterAgent"]
