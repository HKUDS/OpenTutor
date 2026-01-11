#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Question Validation Workflow: retrieve -> validate -> return.

Uses unified LLM Factory for all LLM calls, supporting:
- Cloud providers (OpenAI, Anthropic, DeepSeek, etc.)
- Local providers (Ollama, LM Studio, vLLM, etc.)
- Automatic retry with exponential backoff
"""

from collections.abc import Callable
import json
import os
from pathlib import Path
import sys
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.logging import get_logger
from src.services.config import get_agent_params, load_config_with_main
from src.services.llm import complete as llm_complete
from src.services.llm.capabilities import supports_response_format
from src.services.llm.config import get_llm_config
from src.services.prompt import get_prompt_manager
from src.tools.rag_tool import rag_search

# Module logger
logger = get_logger("QuestionValidation")


class QuestionValidationWorkflow:
    """Question validation workflow - fixed pipeline"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        model: str | None = None,
        kb_name: str | None = None,
        token_stats_callback: Callable | None = None,
        language: str = "en",
    ):
        """
        Initialize validation workflow.

        Args:
            api_key: API key
            base_url: API endpoint
            api_version: API version (for Azure OpenAI)
            model: Model name
            kb_name: Knowledge base name
            token_stats_callback: Callback function to update token statistics
            language: Language for prompts ("en" or "zh")
        """
        # Load LLM configuration via unified config system
        try:
            llm_config = get_llm_config()
            self.api_key = api_key or llm_config.api_key
            self.base_url = base_url or llm_config.base_url
            self.api_version = api_version or llm_config.api_version
            self.binding = llm_config.binding or "openai"
            self.model = model or llm_config.model
        except Exception:
            # Fallback to environment variables
            self.api_key = api_key or os.getenv("LLM_API_KEY")
            self.base_url = base_url or os.getenv("LLM_HOST")
            self.api_version = api_version or os.getenv("LLM_API_VERSION")
            self.binding = os.getenv("LLM_BINDING", "openai")
            self.model = model or os.getenv("LLM_MODEL")

        if not self.model:
            from src.services.llm.exceptions import LLMConfigError
            raise LLMConfigError(
                "LLM_MODEL not configured. Please set it in .env or activate a provider."
            )

        self.kb_name = kb_name
        self.token_stats_callback = token_stats_callback
        self.language = language

        # Load prompts using unified PromptManager
        self._prompts = get_prompt_manager().load_prompts(
            module_name="question",
            agent_name="validation_workflow",
            language=language,
        )

        # Get agent parameters from unified config
        self._agent_params = get_agent_params("question")

        # Load config for RAG settings
        self._config = load_config_with_main("question_config.yaml", project_root)

    async def validate(
        self, question: dict[str, Any], reference_question: str | None = None
    ) -> dict[str, Any]:
        """
        Validate question - fixed pipeline: retrieve → validate → return

        Args:
            question: Question content
                {
                    "question_type": str,
                    "question": str,
                    "options": Dict (for multiple choice),
                    "correct_answer": str,
                    "explanation": str,
                    "knowledge_point": str (optional)
                }

        Returns:
            Dict: Validation result
                {
                    "decision": "approve" | "request_modification" | "request_regeneration",
                    "issues": List[str],
                    "suggestions": List[str],
                    "reasoning": str,
                    "retrieved_knowledge": List[Dict]
                }
        """
        logger.info("Starting question validation")

        # Step 1: Retrieve related knowledge
        logger.info("Step 1/2: Retrieving validation knowledge")
        retrieved_knowledge = await self._retrieve_knowledge(question)
        logger.debug(f"Retrieved {len(retrieved_knowledge)} knowledge items")

        # Step 2: Validate question
        logger.info("Step 2/2: Validating question")
        validation_result = await self._validate_question(
            question, retrieved_knowledge, reference_question
        )
        logger.info(f"Validation decision: {validation_result['decision']}")

        # Add retrieved knowledge to result
        validation_result["retrieved_knowledge"] = retrieved_knowledge

        logger.success("Validation completed")

        return validation_result

    async def _generate_retrieval_query(self, question: dict[str, Any]) -> str:
        """Use LLM to generate retrieval query"""
        knowledge_point = question.get("knowledge_point", "")
        question_text = question.get("question", "")
        options = question.get("options", {})
        correct_answer = question.get("correct_answer", "")

        system_prompt = "You are a professional knowledge retrieval expert."

        prompt = f"""Analyze the following question and generate a concise retrieval query to retrieve relevant knowledge from the knowledge base to validate this question.

Question information:
- Knowledge point: {knowledge_point}
- Question: {question_text}
"""

        if options:
            prompt += f"- Options: {json.dumps(options, ensure_ascii=False)}\n"
        if correct_answer:
            prompt += f"- Answer: {correct_answer}\n"

        prompt += """
Please extract the **core knowledge points and concepts** involved in the question and generate a concise retrieval query (no more than 100 words).

Requirements:
1. Extract core mathematical/physical concepts, theorems, methods from the question
2. If specific formulas or algorithms exist, extract key terminology
3. Do not include specific numerical values and details from the question
4. Query should be able to retrieve theoretical knowledge needed to validate the question

Output the retrieval query directly, no additional content.
"""

        # Call LLM via unified Factory (supports all providers with retry)
        response_content = await llm_complete(
            prompt=prompt,
            system_prompt=system_prompt,
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            api_version=self.api_version,
            binding=self.binding,
            temperature=0.3,
        )

        response_content = response_content.strip()

        # Update token statistics if callback is available
        if self.token_stats_callback:
            # Rough estimation: ~4 chars per token
            input_tokens = (len(system_prompt) + len(prompt)) // 4
            output_tokens = len(response_content) // 4
            self.token_stats_callback(
                input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
            )

        # Log LLM call with detailed information
        logger.log_llm_call(
            model=self.model,
            stage="generate_query",
            system_prompt=system_prompt,
            user_prompt=prompt,
            response=response_content,
            agent_name="QuestionValidationWorkflow",
            input_tokens=0,
            output_tokens=0,
            cost=0.0,
            level="DEBUG",
        )

        return response_content

    async def _retrieve_knowledge(self, question: dict[str, Any]) -> list[dict[str, Any]]:
        """Retrieve knowledge needed for validation."""
        # Use LLM to generate retrieval query
        query = await self._generate_retrieval_query(question)

        logger.debug(f"LLM generated query: {query[:100]}...")

        # Get RAG mode from config
        question_cfg = self._config.get("question", {})
        rag_mode = question_cfg.get("rag_mode", "hybrid")

        # Execute retrieval using unified RAG tool
        try:
            result = await rag_search(
                query=query,
                kb_name=self.kb_name,
                mode=rag_mode,
                only_need_context=True,
            )

            # Return retrieval results with raw answer
            retrieved = []
            if result and result.get("answer"):
                retrieved.append(
                    {
                        "query": query,
                        "answer": result.get("answer", ""),
                    }
                )

            return retrieved

        except Exception as e:
            logger.warning(f"Retrieval failed: {e!s}")
            return []

    async def _validate_question(
        self,
        question: dict[str, Any],
        retrieved_knowledge: list[dict[str, Any]],
        reference_question: str = None,
    ) -> dict[str, Any]:
        """Validate question"""
        knowledge_str = self._format_knowledge(retrieved_knowledge)

        question_str = json.dumps(question, ensure_ascii=False, indent=2)

        reference_section = ""
        innovation_section = ""
        if reference_question:
            reference_section = f"""Reference question (for comparison):
{reference_question}
"""
            innovation_section = self._prompts.get("innovation_section", "")

        prompt_template = self._prompts.get("validate", "")
        prompt = prompt_template.format(
            question=question_str,
            reference_section=reference_section,
            innovation_section=innovation_section,
            validation_knowledge=knowledge_str,
        )

        system_prompt = "You are a professional question validation expert who strictly validates questions based on knowledge base content."

        try:
            # Build kwargs for LLM Factory
            llm_kwargs = {
                "temperature": self._agent_params["temperature"],
                "max_tokens": self._agent_params["max_tokens"],
            }

            # Only add response_format if the provider supports it
            if supports_response_format(self.binding, self.model):
                llm_kwargs["response_format"] = {"type": "json_object"}

            # Call LLM via unified Factory (supports all providers with retry)
            response_content = await llm_complete(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
                api_version=self.api_version,
                binding=self.binding,
                **llm_kwargs,
            )

            # Update token statistics if callback is available
            if self.token_stats_callback:
                # Rough estimation: ~4 chars per token
                input_tokens = (len(system_prompt) + len(prompt)) // 4
                output_tokens = len(response_content) // 4
                self.token_stats_callback(
                    input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
                )

            # Log LLM call with detailed information
            logger.log_llm_call(
                model=self.model,
                stage="validate",
                system_prompt=system_prompt,
                user_prompt=prompt,
                response=response_content,
                agent_name="QuestionValidationWorkflow",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                level="DEBUG",
            )

            result = json.loads(response_content)

            # Ensure issues and suggestions are lists (handle case where LLM returns dict)
            issues = result.get("issues", [])
            if not isinstance(issues, list):
                if isinstance(issues, dict):
                    # If issues is a dict, convert to list
                    issues = [issues]
                else:
                    issues = []

            suggestions = result.get("suggestions", [])
            if not isinstance(suggestions, list):
                if isinstance(suggestions, dict):
                    # If suggestions is a dict, convert to list
                    suggestions = [suggestions]
                else:
                    suggestions = []

            return {
                "decision": result.get("decision", "request_regeneration"),
                "issues": issues,
                "suggestions": suggestions,
                "reasoning": result.get("reasoning", ""),
            }

        except Exception as e:
            logger.warning(f"Validation failed: {e!s}")
            return {
                "decision": "request_regeneration",
                "issues": [f"Validation error: {e!s}"],
                "suggestions": ["Please regenerate the question"],
                "reasoning": "An error occurred during validation",
            }

    def _format_knowledge(self, retrieved_knowledge: list[dict[str, Any]]) -> str:
        """Format retrieved knowledge."""
        if not retrieved_knowledge:
            return "No validation knowledge retrieved"

        knowledge_parts = []
        for k in retrieved_knowledge:
            knowledge_parts.append(f"=== Query: {k['query']} ===")
            answer = k.get("answer", "")
            if answer:
                # Truncate very long answers
                if len(answer) > 3000:
                    answer = answer[:3000] + "...[truncated]"
                knowledge_parts.append(answer)
            knowledge_parts.append("")

        return (
            "\n".join(knowledge_parts) if knowledge_parts else "No validation knowledge retrieved"
        )

    async def analyze_extension(
        self, question: dict[str, Any], shared_context: str
    ) -> dict[str, Any]:
        """
        Analyze how a question extends beyond the knowledge base.

        This is called when a question doesn't pass validation after max rounds,
        to provide insights about how it relates to and extends from the KB.

        Args:
            question: The question that wasn't fully validated
            shared_context: The shared knowledge context from RAG

        Returns:
            Dict with:
                - kb_connection: How the question relates to the knowledge base
                - extended_aspect: What knowledge areas the question extends to
                - reasoning: Detailed explanation
        """
        logger.info("Analyzing question extension from knowledge base")

        question_str = json.dumps(question, ensure_ascii=False, indent=2)

        # Truncate context if too long
        context_str = shared_context
        if len(context_str) > 4000:
            context_str = context_str[:4000] + "...[truncated]"

        system_prompt = "You are an educational content analyst specializing in identifying knowledge connections and learning extensions."

        prompt = f"""Analyze how the following question relates to and extends from the knowledge base content.

Question:
{question_str}

Knowledge Base Content:
{context_str}

Please analyze from the perspective of knowledge extension and provide a JSON response:
{{
    "kb_connection": "Describe how this question connects to the knowledge base content. What concepts, theories, or methods from the KB are relevant to this question?",
    "extended_aspect": "Describe what knowledge areas this question extends to beyond the core KB content. What additional concepts, applications, or perspectives does it explore?",
    "reasoning": "Provide a detailed explanation of the relationship between this question and the knowledge base, and why this extension is valuable for learning."
}}

Guidelines:
1. Focus on the POSITIVE aspects - this is an "extended" question that goes beyond basic KB content
2. kb_connection should identify the foundation concepts from the KB that the question builds upon
3. extended_aspect should highlight what new learning opportunities this question provides
4. Keep the analysis constructive and educational

Output only the JSON, no additional text."""

        try:
            # Build kwargs for LLM Factory
            llm_kwargs = {"temperature": 0.3}

            # Only add response_format if the provider supports it
            if supports_response_format(self.binding, self.model):
                llm_kwargs["response_format"] = {"type": "json_object"}

            # Call LLM via unified Factory (supports all providers with retry)
            response_content = await llm_complete(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
                api_version=self.api_version,
                binding=self.binding,
                **llm_kwargs,
            )

            # Update token statistics
            if self.token_stats_callback:
                input_tokens = (len(system_prompt) + len(prompt)) // 4
                output_tokens = len(response_content) // 4
                self.token_stats_callback(
                    input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
                )

            result = json.loads(response_content)

            logger.info("Extension analysis completed")

            return {
                "kb_connection": result.get("kb_connection", ""),
                "extended_aspect": result.get("extended_aspect", ""),
                "reasoning": result.get("reasoning", ""),
            }

        except Exception as e:
            logger.warning(f"Extension analysis failed: {e!s}")
            return {
                "kb_connection": "Unable to analyze connection to knowledge base",
                "extended_aspect": "This question explores areas beyond the core knowledge base content",
                "reasoning": f"Analysis could not be completed: {e!s}",
            }

    async def analyze_relevance(
        self,
        question: dict[str, Any],
        knowledge_summary: str,
    ) -> dict[str, Any]:
        """
        Analyze the relevance between a question and the knowledge base content.

        This is used in custom mode where we don't iterate - we just analyze
        how the question relates to the knowledge base.

        Args:
            question: The generated question dict
            knowledge_summary: Summary of background knowledge from RAG

        Returns:
            Dict with:
                - relevance: "high" or "partial"
                - kb_coverage: Description of what KB content the question tests
                - extension_points: Description of any extensions (only if partial)
        """
        logger.info("Analyzing question relevance to knowledge base")

        question_str = json.dumps(question, ensure_ascii=False, indent=2)

        # Truncate context if too long
        context_str = knowledge_summary
        if len(context_str) > 4000:
            context_str = context_str[:4000] + "...[truncated]"

        system_prompt = "You are an educational content analyst specializing in analyzing the relationship between exam questions and knowledge base content."

        prompt = f"""Analyze the relevance between the following exam question and the knowledge base content.

Question:
{question_str}

Knowledge Base Content:
{context_str}

Please analyze and provide a JSON response with the following structure:
{{
    "relevance": "high" or "partial",
    "kb_coverage": "Describe specifically what concepts, theories, or methods from the knowledge base this question tests. List the key knowledge points that are directly relevant.",
    "extension_points": "If relevance is 'partial', describe what aspects of this question extend beyond the knowledge base content. What additional knowledge does it require? Leave empty if relevance is 'high'."
}}

Guidelines for determining relevance:
1. "high" - The question can be fully answered using only the knowledge base content. All concepts, methods, and required knowledge are present in the KB.
2. "partial" - The question is related to the KB content but requires some knowledge beyond what's provided. The KB serves as a foundation but the question extends to additional areas.

For kb_coverage:
- Be specific about which concepts from the KB are being tested
- Reference the actual content from the KB where possible
- Explain how the KB content relates to the question

For extension_points (only when relevance is "partial"):
- Identify what additional knowledge is needed
- Explain how the question extends from the KB foundation
- Keep the tone positive - extensions are valuable for learning

Output only the JSON, no additional text."""

        try:
            # Build kwargs for LLM Factory
            llm_kwargs = {"temperature": 0.3}

            # Only add response_format if the provider supports it
            if supports_response_format(self.binding, self.model):
                llm_kwargs["response_format"] = {"type": "json_object"}

            # Call LLM via unified Factory (supports all providers with retry)
            response_content = await llm_complete(
                prompt=prompt,
                system_prompt=system_prompt,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url,
                api_version=self.api_version,
                binding=self.binding,
                **llm_kwargs,
            )

            # Update token statistics
            if self.token_stats_callback:
                input_tokens = (len(system_prompt) + len(prompt)) // 4
                output_tokens = len(response_content) // 4
                self.token_stats_callback(
                    input_tokens=input_tokens, output_tokens=output_tokens, model=self.model
                )

            # Log LLM call
            logger.log_llm_call(
                model=self.model,
                stage="analyze_relevance",
                system_prompt=system_prompt,
                user_prompt=prompt,
                response=response_content,
                agent_name="QuestionValidationWorkflow",
                input_tokens=0,
                output_tokens=0,
                cost=0.0,
                level="DEBUG",
            )

            result = json.loads(response_content)

            relevance = result.get("relevance", "partial")
            if relevance not in ["high", "partial"]:
                relevance = "partial"

            logger.info(f"Relevance analysis completed: {relevance}")

            return {
                "relevance": relevance,
                "kb_coverage": result.get("kb_coverage", ""),
                "extension_points": result.get("extension_points", "")
                if relevance == "partial"
                else "",
            }

        except Exception as e:
            logger.warning(f"Relevance analysis failed: {e!s}")
            return {
                "relevance": "partial",
                "kb_coverage": "Unable to analyze knowledge base coverage",
                "extension_points": f"Analysis could not be completed: {e!s}",
            }
