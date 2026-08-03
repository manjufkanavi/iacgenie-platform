import json

from typing import Dict, Any, Optional, List

from models.iac_state import IaCState

from models.error_classes import ErrorClass

from models.pipeline_phases import PipelinePhase

from .base_agent import BaseAgent

import logging

logger = logging.getLogger(__name__)

CLARIFY_SYSTEM_PROMPT = """You are an Expert Infrastructure-as-Code (IaC) Cloud Architect.

You are interacting with the user in a TWO-WAY CONVERSATION.
Analyze the user's infrastructure request strictly through the lens of
cloud architecture best practices (e.g., the AWS Well-Architected Framework).
Identify missing technical specifications required for a robust production deployment.

CRITICAL INSTRUCTIONS:
1. NEVER ask vague or open-ended questions like "Could you provide more details?".
   You MUST ask specific, targeted technical questions (e.g., about networking topologies, instance classes, storage tiers, or database types).
2. IMPORTANT: Be concise. Ask exactly ONE targeted question at a time. Group related questions if necessary.
3. ALWAYS PROVIDE OPTIONS: You MUST provide a structured `options` array with
   2-4 concrete choices for the user to select from for EVERY question you ask.
   Each option must contain concrete technical values (e.g., "t3.medium", "gp3 SSD", "Multi-AZ RDS").
   Explain the trade-offs in the option descriptions.
   NEVER leave the `options` array empty.
4. CRITICAL RULE - DYNAMIC QUESTIONING: On your FIRST turn ONLY, you MUST analyze the complexity of the user's request. Output an integer `total_questions_estimated` representing exactly how many clarification questions you need to ask to gather all missing details across the following Architectural Checklist:
   - Compute/Workload Needs
   - Networking & Routing
   - Storage & State
   - Security & IAM
   - High Availability & Scaling
   The number of questions should be decided by you based on the nature of the prompt.
5. DO NOT ASSUME ARCHITECTURAL DETAILS. You must not conclude prematurely. Only set `is_complete: true` when you have adequately covered the Architectural Checklist for the given prompt.
6. YOU MUST OUTPUT A SINGLE PURE, VALID JSON OBJECT. Do not wrap the JSON object in markdown blocks (like ```json). Do not output any other text outside the JSON object. Put all your step-by-step reasoning and thinking inside the "thinking" JSON key.

RESPONSE FORMAT:
{
  "thinking": "Write your step-by-step reasoning, analysis of what details are missing, and which question to ask next here.",
  "total_questions_estimated": 5,
  "message": "Brief summary of decisions so far. Your targeted question explaining the context and trade-offs.",
  "options": [
    {
      "label": "2-5 nodes (t3.medium)",
      "value": "2-5_t3.medium",
      "description": "Good for default general purpose workloads."
    },
    {
      "label": "3-10 nodes (m5.large)",
      "value": "3-10_m5.large",
      "description": "Recommended for high-performance databases."
    }
  ],
  "is_complete": false
}

If you have gathered all details and are ready to finalize:
{
  "thinking": "Explain why all details are gathered and we are ready to generate.",
  "message": "All details gathered. Generating infrastructure...",
  "is_complete": true,
  "refined_spec": {
    "provider": "aws",
    "architecture_pattern": "...",
    "resources": [...],
    "tags": {...},
    "outputs": [...]
  }
}"""


class ClarifyAgent(BaseAgent):
    """Agent responsible for clarifying user requests and generating refined specifications."""

    def __init__(self) -> None:
        super().__init__("clarify_agent")
        self.question_count = 0
        self._model_config: Optional[Dict[str, Any]] = None
        self._conversation_history: List[Dict[str, str]] = []

    async def initialize(
        self, state: IaCState, model_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Initialize the clarify agent."""
        await super().initialize(state)
        self.question_count = 0
        self._model_config = model_config
        self._conversation_history = []
        return True

    def set_model_config(self, config: Dict[str, Any]) -> None:
        """Set the model config for LLM calls (can be called after initialize)."""
        self._model_config = config

    def add_conversation_turn(self, role: str, content: str) -> None:
        """Track conversation turns for multi-turn clarification."""
        self._conversation_history.append({"role": role, "content": content})

    async def execute(self) -> Dict[str, Any]:
        """
        Execute the clarify agent logic.
        Returns:
            Dictionary with execution results including:
            - success: bool
            - refined_spec: optional refined specification
            - questions: optional list of clarification questions
            - next_phase: next pipeline phase
            - error: optional error details
        """
        try:
            # Check if we already have a refined spec (skip clarification)
            if self.state is not None and self.state.refined_spec:
                self.log_message(
                    "Refined specification already exists, skipping clarification"
                )
                return {
                    "success": True,
                    "next_phase": PipelinePhase.GENERATE,
                    "result": {"message": "Using existing refined specification"},
                }
            # Check if this is a retry with human feedback
            if self.state is not None and self.state.retry_feedback:
                self.log_message(
                    "Warning: retry_feedback is deprecated, use clarification_history instead."
                )
            # Main clarification logic
            return await self._perform_clarification()
        except Exception as e:
            import traceback

            logger.error(f"ClarifyAgent execution failed: {e}")
            logger.error(traceback.format_exc())
            error_result = await self.handle_error(e)
            return {
                "success": False,
                "error": str(e),
                "error_class": error_result["error_class"],
                "next_phase": PipelinePhase.ESCALATE,
            }

    def _validate_response(self, result: Dict[str, Any]) -> Optional[str]:
        """Validate the parsed LLM response against the expected schema and constraints."""
        if not isinstance(result, dict):
            return "Response must be a JSON object."

        if "is_complete" not in result:
            return "Response must contain 'is_complete' key."

        is_complete = result.get("is_complete")
        if not isinstance(is_complete, bool):
            return "'is_complete' must be a boolean."

        if is_complete:
            if "refined_spec" not in result:
                return (
                    "Response must contain 'refined_spec' key when is_complete is true."
                )
            if not isinstance(result["refined_spec"], dict):
                return "'refined_spec' must be a JSON object."
        else:
            # Check message
            message = result.get("message")
            if not message or not isinstance(message, str) or len(message.strip()) < 15:
                return "Response must contain a non-empty 'message' describing the question."

            # Check for vague questions
            vague_phrases = [
                "provide more details",
                "provide details",
                "give more details",
                "what are your requirements",
                "could you clarify",
                "please clarify",
                "vague details",
                "additional details",
            ]
            if any(phrase in message.lower() for phrase in vague_phrases):
                return "The question must be specific and targeted. Do not ask vague questions like 'Could you provide more details?'."

            # Check options
            options = result.get("options")
            if not options or not isinstance(options, list) or len(options) < 2:
                return "Response must contain an 'options' array with at least 2 concrete options."

            for idx, opt in enumerate(options):
                if not isinstance(opt, dict):
                    return f"Option at index {idx} must be a JSON object."
                if "label" not in opt or "value" not in opt:
                    return (
                        f"Option at index {idx} must contain 'label' and 'value' keys."
                    )
                if not opt.get("label") or not opt.get("value"):
                    return f"Option at index {idx} 'label' and 'value' must be non-empty strings."

        return None

    async def _perform_clarification(self) -> Dict[str, Any]:
        """Perform the main clarification process using LLM with retry/validation."""
        self.log_message("Starting LLM-based clarification process")

        if self.state is None:
            raise ValueError("No state available for LLM call")

        user_request = self.state.user_request
        self.log_message(f"Sending prompt to LLM for analysis: {user_request[:100]}...")

        # Build the initial message list
        messages = [
            {"role": "system", "content": CLARIFY_SYSTEM_PROMPT},
        ]
        messages.append({"role": "user", "content": user_request})

        # Add conversation history for multi-turn clarification
        if getattr(self.state, "clarification_history", None):
            for msg in self.state.clarification_history:
                role = msg.get("role")
                if role == "assistant":
                    assistant_json = {
                        "thinking": "Architectural reasoning for the question.",
                        "message": msg.get("content", ""),
                        "options": msg.get("options", []),
                        "is_complete": False,
                    }
                    messages.append(
                        {"role": "assistant", "content": json.dumps(assistant_json)}
                    )
                else:
                    messages.append(
                        {
                            "role": str(role) if role is not None else "",
                            "content": str(msg.get("content") or ""),
                        }
                    )
        elif self._conversation_history:
            for msg in self._conversation_history:
                messages.append({k: v for k, v in msg.items() if k != "options"})

        # Determine the model config to use
        config = await self._get_llm_config_for_clarify()
        if not config:
            raise ValueError("No LLM configuration available for clarification")

        # Run the LLM query & validation loop
        max_attempts = 3
        last_error = None

        for attempt in range(1, max_attempts + 1):
            self.log_message(
                f"Clarification LLM query attempt {attempt}/{max_attempts}"
            )
            try:
                response_text = await self._llm_chat(messages, config)
                result = self._parse_llm_response(response_text)

                if result is None:
                    raise ValueError(
                        f"Failed to parse LLM response as JSON: {response_text[:200]}"
                    )

                validation_error = self._validate_response(result)
                if validation_error:
                    self.log_message(
                        f"Response validation failed: {validation_error}", "warning"
                    )
                    raise ValueError(
                        f"Invalid JSON schema or content: {validation_error}"
                    )

                # Success! Track the conversation turn
                self.add_conversation_turn("user", user_request)
                self.add_conversation_turn("assistant", response_text)

                # Process the valid clarification result and return
                return await self._process_clarification_result(result)

            except Exception as e:
                last_error = e
                self.log_message(f"Attempt {attempt} failed: {str(e)}", "warning")

                # Append failed assistant response and corrective instruction to messages history
                if "response_text" in locals():
                    messages.append({"role": "assistant", "content": response_text})
                else:
                    messages.append({"role": "assistant", "content": "{}"})

                feedback = (
                    f"CRITICAL ERROR: Your previous response was invalid. "
                    f"Details: {str(e)}\n"
                    f"Please correct the error, ensure your reasoning is inside the 'thinking' key of the JSON object, "
                    f"and output a single PURE, VALID JSON object with all required keys."
                )
                messages.append({"role": "user", "content": feedback})

        # If all attempts failed, propagate the last error
        raise last_error or ValueError("All clarification attempts failed.")

    async def _get_llm_config_for_clarify(self) -> Optional[Dict[str, Any]]:
        """Build or retrieve an LLM config suitable for clarification calls.

        Priority: model_config (from orchestrator) -> DB -> ai_service registry -> local fallback.
        """
        raw_config = None
        if self._model_config:
            raw_config = self._model_config
        else:
            # Try loading from DB first
            try:
                from app_factory import db_provider

                if self.state:
                    metadata = getattr(self.state, "metadata", {})
                    if isinstance(metadata, dict):
                        project_id = metadata.get("project_id")
                        if project_id:
                            configs = await db_provider.list_model_configs(
                                uid="", project_id=project_id
                            )
                            if isinstance(configs, list) and len(configs) > 0:
                                raw_config = configs[0]
            except Exception as e:
                self.log_message(f"Failed to load LLM config from DB: {e}", "warning")

        if raw_config:
            # Normalize configuration (handles both raw database config rows and partially normalized configs)
            config_dict = (
                raw_config.get("config", {})
                if isinstance(raw_config.get("config"), dict)
                else {}
            )

            # Resolve base_url
            base_url = raw_config.get("base_url") or config_dict.get("base_url")
            provider = raw_config.get("provider", "custom")
            if not base_url and provider == "lmstudio":
                base_url = "http://127.0.0.1:1234/v1"

            # Resolve api_key
            api_key = raw_config.get("api_key")
            if not api_key or api_key == "":
                api_key = "dummy"

            # Resolve temperature
            temp_raw = raw_config.get("temperature")
            if temp_raw is None:
                temp = 0.1
            else:
                try:
                    temp = float(temp_raw)
                    if temp > 2.0:  # DB might store 70 instead of 0.7
                        temp = temp / 100.0
                except (ValueError, TypeError):
                    temp = 0.1

            return {
                "provider": provider,
                "model_name": raw_config.get("model_name")
                or raw_config.get("model")
                or "Qwen3.6-27B-UD-MLX-4bit",
                "api_key": api_key,
                "base_url": base_url,
                "max_tokens": raw_config.get("max_tokens")
                or config_dict.get("max_tokens")
                or 8192,
                "temperature": temp,
                "timeout": raw_config.get("timeout")
                or config_dict.get("timeout")
                or 120,
            }

        try:
            from services.ai_service import ai_service

            provider_name = None
            if self.state and getattr(self.state, "model_routing", None):
                provider_name = self.state.model_routing.get("provider")

            config = None
            if provider_name and provider_name in ai_service.registry.provider_configs:
                config = ai_service.registry.provider_configs[provider_name]
            elif ai_service.registry.fallback_order:
                best_provider = ai_service.registry.fallback_order[0]
                config = ai_service.registry.provider_configs[best_provider]

            if config:
                return {
                    "provider": config.provider,
                    "model_name": config.model_name,
                    "api_key": config.api_key,
                    "base_url": config.base_url,
                    "max_tokens": config.max_tokens,
                    "temperature": config.temperature,
                    "timeout": config.timeout,
                }
        except Exception as e:
            self.log_message(
                f"Failed to load LLM config from ai_service: {e}", "warning"
            )

        # Local fallback: openai-compatible model at 127.0.0.1:1234
        return {
            "provider": "openai",
            "model_name": "Qwen3.6-27B-UD-MLX-4bit",
            "api_key": "dummy",
            "base_url": "http://127.0.0.1:1234/v1",
            "max_tokens": 8192,
            "temperature": 0.1,
            "timeout": 120,
        }

    async def _llm_chat(
        self, messages: List[Dict[str, str]], config: Dict[str, Any]
    ) -> str:
        """Make a chat completion call via the LLM Proxy with direct litellm fallback."""
        # Try LLM Proxy first
        try:
            from src.llm_proxy.models import LLMRequest, LLMMessage
            from src.llm_proxy.service import get_llm_service

            llm_req = LLMRequest(  # type: ignore[call-arg]
                model=config.get("model_name", "Qwen3.6-27B-UD-MLX-4bit"),
                messages=[
                    LLMMessage(role=m["role"], content=m["content"])  # type: ignore[arg-type]
                    for m in messages
                ],
                temperature=config.get("temperature", 0.1),
                max_tokens=config.get("max_tokens", 8192),
            )

            llm_service = get_llm_service()
            result = await llm_service.generate_completion(
                request=llm_req,
                model_config=config,
                cache_enabled=True,
                rate_limit_enabled=True,
            )

            if result.response and result.response.choices:
                return result.response.choices[0].text.strip()
            else:
                raise ValueError(f"LLM Proxy returned empty response: {result}")
        except Exception as proxy_err:
            self.log_message(
                f"LLM Proxy call failed, falling back to direct litellm: {proxy_err}",
                "warning",
            )

        # Fallback: direct litellm.acompletion
        import litellm

        provider = config.get("provider", "openai")
        model = config.get("model_name", "Qwen3.6-27B-UD-MLX-4bit")
        api_key = config.get("api_key")
        base_url = config.get("base_url")

        if provider == "openai":
            litellm_model = model
        elif provider in ["custom", "lmstudio"]:
            litellm_model = f"openai/{model}"
        elif provider == "ollama":
            litellm_model = f"ollama/{model}"
        elif provider == "claude":
            litellm_model = f"anthropic/{model}"
        else:
            litellm_model = f"{provider}/{model}"

        kwargs: Dict[str, Any] = {
            "model": litellm_model,
            "messages": messages,
            "temperature": config.get("temperature", 0.1),
            "max_tokens": config.get("max_tokens", 8192),
        }

        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["api_base"] = base_url

        if provider in ["openai", "mistral", "custom", "lmstudio", "ollama"]:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await litellm.acompletion(**kwargs)
            if not response.choices:
                raise ValueError("LLM returned empty choices array")
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LiteLLM API error: {e}")

    def _parse_llm_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from LLM response."""
        text = response_text.strip()

        # Strip out <think> blocks (DeepSeek/Qwen)
        import re

        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # Try to extract from markdown code block
        match = re.search(r"```(?:json)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            text = match.group(1).strip()
        else:
            # Fallback: try to find the first { or [ and last } or ]
            start_dict = text.find("{")
            start_list = text.find("[")
            start = -1
            if start_dict != -1 and start_list != -1:
                start = min(start_dict, start_list)
            else:
                start = max(start_dict, start_list)

            end_dict = text.rfind("}")
            end_list = text.rfind("]")
            end = max(end_dict, end_list)

            if start != -1 and end != -1 and end >= start:
                text = text[start : end + 1]
            elif start != -1:
                # Truncated response, try to repair by appending missing braces
                text = text[start:]

        # Attempt to repair truncated JSON
        suffixes_to_try = [
            "",
            "}",
            "}]",
            '"}',
            '"]',
            "]}",
            '"}]',
            '" }]',
            '"} ]',
            '"}',
            "]",
            " }",
        ]
        for suffix in suffixes_to_try:
            try:
                parsed = json.loads(text + suffix)
                # If parsed is a list, check if it's actually wrapping our expected dict
                if isinstance(parsed, list):
                    if (
                        len(parsed) > 0
                        and isinstance(parsed[0], dict)
                        and "message" in parsed[0]
                    ):
                        return parsed[0]
                    # Otherwise, assume it's an array of options
                    return {
                        "message": "Please select an option from below:",
                        "options": parsed,
                        "is_complete": False,
                    }
                return parsed
            except json.JSONDecodeError:
                continue

        return None

    async def _process_clarification_result(
        self, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process the LLM's clarification result and update state accordingly."""
        if not result.get("is_complete", False):
            message = result.get("message", "Please clarify your request further.")
            options = result.get("options", [])

            if not options:
                raise ValueError(
                    "Model failed to provide choices for the question. The options array MUST NOT be empty."
                )

            # Handle the case where the LLM double-encodes the JSON inside the message key
            if isinstance(message, str) and message.strip().startswith("{"):
                try:
                    import json as _json

                    parsed_msg = _json.loads(message)
                    if isinstance(parsed_msg, dict):
                        if "message" in parsed_msg:
                            message = parsed_msg["message"]
                        if not options and "options" in parsed_msg:
                            options = parsed_msg["options"]
                except Exception:
                    pass

            # If the model hallucinates a nested response inside the options array, extract it
            if (
                options
                and isinstance(options, list)
                and len(options) == 1
                and isinstance(options[0], dict)
            ):
                if "message" in options[0]:
                    message = options[0]["message"]
                    options = options[0].get("options", [])

            # Validate options to prevent hallucinated nested JSON
            sanitized_options: list[dict[str, Any] | str] = []
            for opt in options:
                if isinstance(opt, dict):
                    # If the option contains "message" or "options", it's a hallucination of the root format
                    if "message" in opt or "options" in opt:
                        continue
                    # Only keep options with a valid label or value
                    if "label" in opt or "value" in opt or "name" in opt:
                        sanitized_options.append(opt)
                elif isinstance(opt, str):
                    sanitized_options.append(opt)
            options = sanitized_options

            # If options list is empty, construct a valid set of default options and preserve the message
            if not options:
                if (
                    not message
                    or len(message.strip()) < 20
                    or "provide more details" in message.lower()
                    or "clarify" in message.lower()
                ):
                    message = (
                        "Could you provide more specific technical details "
                        "about your desired architecture? "
                        "(e.g. instance types, node count, security requirements)"
                    )
                options = [
                    {
                        "label": "Standard Setup",
                        "value": "standard_setup",
                        "description": "Use standard production-ready defaults and best practices.",
                    },
                    {
                        "label": "Custom Configuration",
                        "value": "custom_config",
                        "description": "Provide custom technical specifications in the next step.",
                    },
                ]

            # Dynamically calculate true question count from history
            history_len = (
                len(self.state.clarification_history)
                if self.state and getattr(self.state, "clarification_history", None)
                else 0
            )
            self.question_count = history_len // 2

            # Extract total_questions_estimated if available
            if "total_questions_estimated" in result and self.state is not None:
                try:
                    estimated = int(result["total_questions_estimated"])
                    if (
                        getattr(self.state, "expected_clarification_questions", None)
                        is None
                    ):
                        self.state.expected_clarification_questions = estimated
                        self.log_message(
                            f"Model estimated {estimated} clarification questions needed."
                        )
                except (ValueError, TypeError):
                    pass

            dynamic_limit = (
                getattr(self.state, "expected_clarification_questions", None)
                if self.state
                else None
            )
            # Default safety limit if model failed to provide one
            if dynamic_limit is None:
                dynamic_limit = 5

            # Enforce absolute maximum of 20 questions
            dynamic_limit = min(dynamic_limit, 20)

            if self.question_count >= dynamic_limit:
                self.log_message(
                    f"Reached estimated limit of {dynamic_limit} questions, forcing completion",
                    "warning",
                )
                # Force completion with whatever details we have
                refined_spec = result.get(
                    "refined_spec",
                    {
                        "provider": "aws",
                        "resources": [],
                        "tags": {"ManagedBy": "agentic-loop"},
                    },
                )
                if self.state is not None:
                    self.state.refined_spec = json.dumps(refined_spec)
                return {
                    "success": True,
                    "next_phase": PipelinePhase.GENERATE,
                    "result": {
                        "refined_spec": refined_spec,
                        "message": "Maximum questions reached. Proceeding with best assumptions...",
                    },
                }

            if self.state is not None:
                self.state.retry_feedback = json.dumps(
                    {"message": message, "options": options}
                )

            return {
                "success": False,
                "error": "Clarification needed",
                "error_class": ErrorClass.CLARIFICATION,
                "next_phase": PipelinePhase.ESCALATE,
                "questions": [message],
                "options": options,
                "message": message,
            }
        else:
            refined_spec = result.get("refined_spec", {})
            if self.state is not None:
                self.state.refined_spec = json.dumps(refined_spec)
            self.log_message("Clarification completed successfully with refined spec")
            return {
                "success": True,
                "next_phase": PipelinePhase.GENERATE,
                "result": {
                    "refined_spec": refined_spec,
                    "message": result.get("message", "Clarification completed"),
                },
            }

    async def _handle_retry_with_feedback(self) -> Dict[str, Any]:
        """Handle multi-turn clarification: pass user answers back to LLM for re-analysis."""
        if self.state is None:
            return {
                "success": False,
                "error": "No state available for retry handling",
                "error_class": ErrorClass.FATAL,
                "next_phase": PipelinePhase.ESCALATE,
            }
        feedback = self.state.retry_feedback
        if not feedback:
            return {
                "success": False,
                "error": "No feedback provided for retry",
                "error_class": ErrorClass.CLARIFICATION,
                "next_phase": PipelinePhase.ESCALATE,
            }
        # Parse feedback — it's a list of user answers
        feedback_data = json.loads(feedback)
        if not isinstance(feedback_data, list):
            # Not a list of answers, treat as questions still needing answers
            return {
                "success": False,
                "error": "Questions require human answers",
                "error_class": ErrorClass.CLARIFICATION,
                "next_phase": PipelinePhase.ESCALATE,
                "questions": feedback_data
                if isinstance(feedback_data, list)
                else [str(feedback_data)],
            }

        # Build the answers string to send to LLM (if needed in future)
        # answers_text = "\n".join(
        #     f"Q{i + 1}: {a}" for i, a in enumerate(feedback_data)
        # )

        # Send answers to LLM for re-evaluation
        user_request = self.state.user_request
        llm_messages = [
            {"role": "system", "content": CLARIFY_SYSTEM_PROMPT},
            {"role": "user", "content": f"Original Request: {user_request}"},
        ]
        # Add prior conversation history (which already includes the user's latest answer)
        llm_messages.extend(self._conversation_history)

        # Get config
        config = await self._get_llm_config_for_clarify()
        if not config:
            raise ValueError("No LLM configuration available for clarification retry")

        # Call LLM
        response_text = await self._llm_chat(llm_messages, config)
        result = self._parse_llm_response(response_text)

        if result is None:
            raise ValueError(
                f"Failed to parse LLM response for retry: {response_text[:200]}"
            )

        return await self._process_clarification_result(result)

    async def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors specific to the clarify agent."""
        error_class = self.classify_error(error)
        # Custom error handling for clarification
        if "JSON" in str(error) or "serialization" in str(error):
            error_class = ErrorClass.CLARIFICATION
        return {
            "error_class": error_class,
            "message": f"Clarification error: {str(error)}",
            "can_retry": error_class == ErrorClass.RETRYABLE,
            "retry_feedback": f"Error during clarification: {str(error)}",
        }
