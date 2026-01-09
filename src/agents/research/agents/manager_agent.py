#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ManagerAgent - Queue management Agent
Responsible for managing DynamicTopicQueue state and task distribution
"""

import asyncio
from pathlib import Path
import sys
from typing import Any

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.agents.base_agent import BaseAgent
from src.agents.research.data_structures import DynamicTopicQueue, TopicBlock


class ManagerAgent(BaseAgent):
    """Queue management Agent"""

    def __init__(
        self,
        config: dict[str, Any],
        api_key: str = None,
        base_url: str = None,
        api_version: str = None,
    ):
        language = config.get("system", {}).get("language", "zh")
        super().__init__(
            module_name="research",
            agent_name="manager_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
            config=config,
        )
        self.queue: DynamicTopicQueue | None = None
        self.primary_topic: str | None = None
        self._lock = asyncio.Lock()  # Lock for thread-safe operations in parallel mode

    def set_queue(self, queue: DynamicTopicQueue) -> None:
        """Set queue to manage"""
        self.queue = queue

    def set_primary_topic(self, topic: str | None) -> None:
        """Update primary research topic for subsequent topic consistency judgment"""
        self.primary_topic = (topic or "").strip() or None

    def get_next_task(self) -> TopicBlock | None:
        """
        Get next task to research

        Returns:
            Next TopicBlock with PENDING status, returns None if none available
        """
        if not self.queue:
            return None

        block = self.queue.get_pending_block()
        if block:
            # Mark as researching
            self.queue.mark_researching(block.block_id)
            print(f"\n📋 ManagerAgent: Assigned task {block.block_id}")
            print(f"   Topic: {block.sub_topic}")

        return block

    def complete_task(self, block_id: str) -> bool:
        """
        Mark task as completed

        Args:
            block_id: Topic block ID

        Returns:
            Whether successfully marked
        """
        if not self.queue:
            return False

        success = self.queue.mark_completed(block_id)
        if success:
            print(f"✓ ManagerAgent: Task {block_id} completed")

        return success

    async def get_next_task_async(self) -> TopicBlock | None:
        """
        Thread-safe async version of get_next_task for parallel mode

        Returns:
            Next TopicBlock with PENDING status, returns None if none available
        """
        async with self._lock:
            return self.get_next_task()

    async def complete_task_async(self, block_id: str) -> bool:
        """
        Thread-safe async version of complete_task for parallel mode

        Args:
            block_id: Topic block ID

        Returns:
            Whether successfully marked
        """
        async with self._lock:
            return self.complete_task(block_id)

    async def fail_task_async(self, block_id: str, reason: str = "") -> bool:
        """
        Thread-safe async version of fail_task for parallel mode

        Args:
            block_id: Topic block ID
            reason: Failure reason

        Returns:
            Whether successfully marked
        """
        async with self._lock:
            return self.fail_task(block_id, reason)

    async def add_new_topic_async(self, sub_topic: str, overview: str) -> TopicBlock:
        """
        Thread-safe async version of add_new_topic for parallel mode

        Args:
            sub_topic: Sub-topic name
            overview: Topic overview

        Returns:
            Newly created TopicBlock
        """
        async with self._lock:
            return self.add_new_topic(sub_topic, overview)

    def fail_task(self, block_id: str, reason: str = "") -> bool:
        """
        Mark task as failed

        Args:
            block_id: Topic block ID
            reason: Failure reason

        Returns:
            Whether successfully marked
        """
        if not self.queue:
            return False

        success = self.queue.mark_failed(block_id)
        if success:
            print(f"✗ ManagerAgent: Task {block_id} failed")
            if reason:
                print(f"   Reason: {reason}")

        return success

    def add_new_topic(self, sub_topic: str, overview: str) -> TopicBlock:
        """
        Add new topic to queue

        Args:
            sub_topic: Sub-topic name
            overview: Topic overview

        Returns:
            Newly created TopicBlock
        """
        if not self.queue:
            raise RuntimeError("Queue not initialized")

        normalized = (sub_topic or "").strip()
        if not normalized:
            raise ValueError("New topic title cannot be empty")
        if self.queue.has_topic(normalized):
            print(f"⚠️ ManagerAgent: Topic《{normalized}》already exists, skipping addition")
            return None

        block = self.queue.add_block(normalized, overview)
        print(f"✓ ManagerAgent: Added new topic {block.block_id}")
        print(f"   Topic: {sub_topic}")

        return block

    def is_research_complete(self) -> bool:
        """
        Check if research is complete (all tasks are completed)

        Returns:
            Whether all tasks are completed
        """
        if not self.queue:
            return False

        return self.queue.is_all_completed()

    def get_queue_status(self) -> dict[str, Any]:
        """
        Get queue status

        Returns:
            Queue statistics
        """
        if not self.queue:
            return {}

        stats = self.queue.get_statistics()
        print("\n📊 Queue Status:")
        print(f"   Total Topics: {stats['total_blocks']}")
        print(f"   Pending: {stats['pending']}")
        print(f"   Researching: {stats['researching']}")
        print(f"   Completed: {stats['completed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Total Tool Calls: {stats['total_tool_calls']}")

        return stats

    async def process(self, *args, **kwargs) -> Any:
        """Main processing logic of Manager Agent"""
        # Manager Agent is mainly called through other methods, no independent process method needed


__all__ = ["ManagerAgent"]
