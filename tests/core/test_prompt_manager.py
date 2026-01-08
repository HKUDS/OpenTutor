#!/usr/bin/env python
"""
Unit tests for the unified PromptManager.
"""

from src.core.prompt_manager import PromptManager, get_prompt_manager


class TestPromptManager:
    """Test cases for PromptManager."""

    def setup_method(self):
        """Reset singleton and cache before each test."""
        PromptManager.reset_singleton()

    def test_singleton_pattern(self):
        """Test that PromptManager uses singleton pattern."""
        pm1 = PromptManager()
        pm2 = PromptManager()
        assert pm1 is pm2

    def test_get_prompt_manager_returns_singleton(self):
        """Test that get_prompt_manager returns the same instance."""
        pm1 = get_prompt_manager()
        pm2 = get_prompt_manager()
        assert pm1 is pm2

    def test_load_prompts_research_module(self):
        """Test loading prompts for research module."""
        pm = get_prompt_manager()
        prompts = pm.load_prompts(
            module_name="research",
            agent_name="research_agent",
            language="en",
        )
        assert isinstance(prompts, dict)
        # research_agent should have system section
        assert "system" in prompts or prompts == {}

    def test_load_prompts_solve_module(self):
        """Test loading prompts for solve module."""
        pm = get_prompt_manager()
        prompts = pm.load_prompts(
            module_name="solve",
            agent_name="solve_agent",
            language="en",
        )
        assert isinstance(prompts, dict)

    def test_load_prompts_guide_module(self):
        """Test loading prompts for guide module."""
        pm = get_prompt_manager()
        prompts = pm.load_prompts(
            module_name="guide",
            agent_name="chat_agent",
            language="en",
        )
        assert isinstance(prompts, dict)

    def test_load_prompts_with_subdirectory(self):
        """Test loading prompts with subdirectory (e.g., solve_loop)."""
        pm = get_prompt_manager()
        prompts = pm.load_prompts(
            module_name="solve",
            agent_name="solve_agent",
            language="en",
            subdirectory="solve_loop",
        )
        assert isinstance(prompts, dict)

    def test_caching(self):
        """Test that prompts are cached after first load."""
        pm = get_prompt_manager()

        # First load
        prompts1 = pm.load_prompts("research", "research_agent", "en")

        # Second load should return cached version
        prompts2 = pm.load_prompts("research", "research_agent", "en")

        assert prompts1 is prompts2

    def test_clear_cache_all(self):
        """Test clearing all cache."""
        pm = get_prompt_manager()

        # Load some prompts
        pm.load_prompts("research", "research_agent", "en")
        pm.load_prompts("guide", "chat_agent", "en")

        assert hasattr(pm, "cache")
        assert len(pm.cache) == 2

        pm.clear_cache()
        assert len(pm.cache) == 0

    def test_clear_cache_module_specific(self):
        """Test clearing cache for specific module."""
        pm = get_prompt_manager()

        # Load prompts for multiple modules
        pm.load_prompts("research", "research_agent", "en")
        pm.load_prompts("guide", "chat_agent", "en")

        assert len(pm.cache) == 2

        # Clear only research cache
        pm.clear_cache("research")

        # Guide prompts should still be cached
        assert len(pm.cache) == 1
        assert any(k.startswith("guide_") for k in pm.cache)

    def test_get_prompt_helper(self):
        """Test the get_prompt helper method."""
        pm = get_prompt_manager()

        test_prompts: dict[str, dict[str, str] | str] = {
            "system": {
                "role": ("You are a helpful assistant"),
                "task": ("Answer questions"),
            },
            "simple_key": "Simple value",
        }

        # Test nested access
        role = pm.get_prompt(test_prompts, "system", "role")
        assert role == "You are a helpful assistant"

        # Test simple access (no field)
        simple = pm.get_prompt(test_prompts, "simple_key")
        assert simple == "Simple value"

        # Test fallback
        missing = pm.get_prompt(test_prompts, "nonexistent", "field", "fallback_value")
        assert missing == "fallback_value"

    def test_language_fallback(self):
        """Test language fallback chain."""
        pm = get_prompt_manager()

        # Even with a potentially missing language, should fallback
        prompts = pm.load_prompts("research", "research_agent", "zh")
        assert isinstance(prompts, dict)

    def test_reload_prompts(self):
        """Test force reload bypasses cache."""
        pm = get_prompt_manager()

        # Load and cache
        prompts1 = pm.load_prompts("research", "research_agent", "en")

        # Force reload
        prompts2 = pm.reload_prompts("research", "research_agent", "en")
        # They should be different objects after reload
        assert prompts1 is not prompts2
        # Content may change, identity must differ from cached
        # After reload, cache should have fresh entry
        assert hasattr(pm, "cache")
        # The cached object should be the new one
        prompts3 = pm.load_prompts("research", "research_agent", "en")
        assert prompts2 is prompts3


class TestPromptManagerLanguages:
    """Test language handling."""

    def setup_method(self):
        """Reset singleton and cache before each test."""
        PromptManager.reset_singleton()

    def test_english_prompts(self):
        """Test loading English prompts."""
        pm = get_prompt_manager()
        prompts = pm.load_prompts("guide", "chat_agent", "en")
        assert isinstance(prompts, dict)

    def test_chinese_prompts(self):
        """Test loading Chinese prompts."""
        pm = get_prompt_manager()
        prompts = pm.load_prompts("guide", "chat_agent", "zh")
        assert isinstance(prompts, dict)

    def test_invalid_language_falls_back(self):
        """Test that invalid language code falls back gracefully."""
        pm = get_prompt_manager()
        # Should not raise, should fallback
        prompts = pm.load_prompts("research", "research_agent", "invalid")
        assert isinstance(prompts, dict)
