
import unittest
from unittest.mock import AsyncMock, patch
from src.services.llm.cloud_provider import _openai_complete, _openai_stream

class TestForcedTemperature(unittest.IsolatedAsyncioTestCase):
    
    async def test_forced_temperature_complete(self):
        """Verify forced temperature override in completion"""
        with patch("src.services.llm.cloud_provider.aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_post_ctx = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {"choices": [{"message": {"content": "test"}}]}
            
            # Setup context manager for post()
            # session.post() returns a context manager, NOT a coroutine
            mock_session.post = unittest.mock.MagicMock() 
            mock_post_ctx.__aenter__.return_value = mock_response
            mock_session.post.return_value = mock_post_ctx
            
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            # Test case 1: gpt-5 should force temperature 1.0
            await _openai_complete(
                model="gpt-5-preview",
                prompt="test",
                system_prompt="sys",
                api_key="key",
                base_url="url",
                temperature=0.7  # specific user request
            )

            # Verify call arguments
            call_args = mock_session.post.call_args
            self.assertIsNotNone(call_args)
            payload = call_args[1]["json"]
            self.assertEqual(payload["model"], "gpt-5-preview")
            self.assertEqual(payload["temperature"], 1.0, "Should force temperature to 1.0 for gpt-5")

            # Test case 2: gpt-4 should respect user temperature
            await _openai_complete(
                model="gpt-4",
                prompt="test",
                system_prompt="sys",
                api_key="key",
                base_url="url",
                temperature=0.5
            )
            
            call_args = mock_session.post.call_args
            payload = call_args[1]["json"]
            self.assertEqual(payload["model"], "gpt-4")
            self.assertEqual(payload["temperature"], 0.5, "Should keep user temperature for gpt-4")

    async def test_forced_temperature_stream(self):
        """Verify forced temperature override in streaming"""
        with patch("src.services.llm.cloud_provider.aiohttp.ClientSession") as mock_session_cls:
            mock_session = AsyncMock()
            mock_post_ctx = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            # Mock streaming response
            mock_response.content.__aiter__.return_value = [
                b'data: {"choices": [{"delta": {"content": "test"}}]}\n\n',
                b'data: [DONE]\n\n'
            ]
            
            # Setup context manager for post()
            mock_session.post = unittest.mock.MagicMock()
            mock_post_ctx.__aenter__.return_value = mock_response
            mock_session.post.return_value = mock_post_ctx
            
            mock_session_cls.return_value.__aenter__.return_value = mock_session

            # Test case: o1 model forcing
            async for _ in _openai_stream(
                model="o1-preview",
                prompt="test",
                system_prompt="sys",
                api_key="key",
                base_url="url",
                temperature=0.1
            ):
                pass

            call_args = mock_session.post.call_args
            payload = call_args[1]["json"]
            self.assertEqual(payload["model"], "o1-preview")
            self.assertEqual(payload["temperature"], 1.0, "Should force temperature to 1.0 for o1")
