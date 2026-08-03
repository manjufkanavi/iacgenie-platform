import os

from typing import Dict, Any, Optional

import logging

logger = logging.getLogger(__name__)


class PromptManager:
    """Manages prompts for the agentic pipeline."""

    def __init__(self, prompts_dir: str = "prompts"):
        self.prompts_dir = prompts_dir
        self.prompt_cache: Dict[str, str] = {}
        self._initialize_prompts_directory()

    def _initialize_prompts_directory(self) -> None:
        """Initialize the prompts directory structure."""
        os.makedirs(self.prompts_dir, exist_ok=True)
        # Create default prompt files if they don't exist
        default_prompts = [
            "clarify_system.txt",
            "generator_system.txt",
            "reviewer_system.txt",
            "static_analysis_system.txt",
        ]
        for prompt_file in default_prompts:
            prompt_path = os.path.join(self.prompts_dir, prompt_file)
            if not os.path.exists(prompt_path):
                self._create_default_prompt(prompt_file)

    def _create_default_prompt(self, prompt_file: str) -> None:
        """Create a default prompt file."""
        prompt_path = os.path.join(self.prompts_dir, prompt_file)
        if "clarify" in prompt_file:
            content = """You are an expert infrastructure requirements clarifier. Your task is to:
1. Analyze the user's infrastructure request

2. Identify any ambiguities or missing requirements

3. Ask clarification questions if needed (max 3 questions)

4. Generate a refined specification in JSON format

Focus on:

- Cloud provider preferences

- Resource requirements

- Security and compliance needs

- Scalability requirements

- Cost constraints

If the request is clear, generate the refined specification directly."""
        elif "generator" in prompt_file:
            content = """You are an expert Terraform HCL code generator. Your task is to:
1. Analyze the refined specification

2. Generate syntactically correct Terraform HCL code

3. Include proper resource definitions

4. Add appropriate tags and metadata

5. Ensure the code follows best practices

Generate code that is:

- Well-formatted and readable

- Modular and reusable

- Secure by default

- Cost-optimized

- Production-ready"""
        elif "reviewer" in prompt_file:
            content = """You are an expert code reviewer for Terraform configurations. Your task is to:
1. Analyze the generated HCL code

2. Identify potential issues and improvements

3. Provide constructive feedback

4. Suggest best practices

Focus on:

- Syntax correctness

- Resource optimization

- Security best practices

- Error handling

- Maintainability"""
        else:  # static_analysis
            content = """You are an expert static analysis tool for Terraform configurations. Your task is to:
1. Analyze HCL code for security violations

2. Check for compliance with best practices

3. Identify potential misconfigurations

4. Classify issues by severity

Focus on:

- Security vulnerabilities

- Compliance violations

- Performance anti-patterns

- Resource leaks

- Deprecation warnings"""
        with open(prompt_path, "w") as f:
            f.write(content.strip())

    def get_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Get a prompt by name.
        Args:
            prompt_name: Name of the prompt
        Returns:
            Dictionary with prompt content
        """
        if prompt_name in self.prompt_cache:
            return {
                "success": True,
                "prompt": self.prompt_cache[prompt_name],
                "source": "cache",
            }
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        if not os.path.exists(prompt_path):
            return {
                "success": False,
                "error": f"Prompt not found: {prompt_name}",
                "error_class": "prompt_not_found",
            }
        try:
            with open(prompt_path, "r") as f:
                content = f.read().strip()
            self.prompt_cache[prompt_name] = content
            return {"success": True, "prompt": content, "source": "file"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "prompt_read_failed",
            }

    def update_prompt(self, prompt_name: str, new_content: str) -> Dict[str, Any]:
        """
        Update a prompt's content.
        Args:
            prompt_name: Name of the prompt
            new_content: New content for the prompt
        Returns:
            Dictionary with update result
        """
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        try:
            with open(prompt_path, "w") as f:
                f.write(new_content.strip())
            # Update cache
            self.prompt_cache[prompt_name] = new_content.strip()
            self.log_message(f"Updated prompt: {prompt_name}")
            return {"success": True, "message": "Prompt updated successfully"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "prompt_update_failed",
            }

    def list_prompts(self) -> Dict[str, Any]:
        """List all available prompts."""
        try:
            prompts = []
            for filename in os.listdir(self.prompts_dir):
                if filename.endswith(".txt"):
                    prompt_name = filename[:-4]
                    prompts.append(prompt_name)
            return {"success": True, "prompts": sorted(prompts), "count": len(prompts)}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "prompt_listing_failed",
            }

    def create_prompt(self, prompt_name: str, content: str) -> Dict[str, Any]:
        """
        Create a new prompt.
        Args:
            prompt_name: Name of the new prompt
            content: Content for the prompt
        Returns:
            Dictionary with creation result
        """
        if not prompt_name.endswith(".txt"):
            prompt_name += ".txt"
        prompt_path = os.path.join(self.prompts_dir, prompt_name)
        if os.path.exists(prompt_path):
            return {
                "success": False,
                "error": f"Prompt already exists: {prompt_name}",
                "error_class": "prompt_exists",
            }
        try:
            with open(prompt_path, "w") as f:
                f.write(content.strip())
            # Update cache
            base_name = (
                prompt_name[:-4] if prompt_name.endswith(".txt") else prompt_name
            )
            self.prompt_cache[base_name] = content.strip()
            self.log_message(f"Created new prompt: {prompt_name}")
            return {"success": True, "message": "Prompt created successfully"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "prompt_creation_failed",
            }

    def delete_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Delete a prompt.
        Args:
            prompt_name: Name of the prompt to delete
        Returns:
            Dictionary with deletion result
        """
        prompt_path = os.path.join(self.prompts_dir, f"{prompt_name}.txt")
        if not os.path.exists(prompt_path):
            return {
                "success": False,
                "error": f"Prompt not found: {prompt_name}",
                "error_class": "prompt_not_found",
            }
        try:
            os.remove(prompt_path)
            # Remove from cache
            if prompt_name in self.prompt_cache:
                del self.prompt_cache[prompt_name]
            self.log_message(f"Deleted prompt: {prompt_name}")
            return {"success": True, "message": "Prompt deleted successfully"}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "prompt_deletion_failed",
            }

    def render_prompt(
        self, prompt_name: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Render a prompt with variables.
        Args:
            prompt_name: Name of the prompt
            variables: Variables to substitute in the prompt
        Returns:
            Dictionary with rendered prompt
        """
        get_result = self.get_prompt(prompt_name)
        if not get_result["success"]:
            return get_result
        prompt_content = get_result["prompt"]
        try:
            rendered = prompt_content
            if variables:
                for key, value in variables.items():
                    placeholder = f"{{{key}}}"
                    rendered = rendered.replace(placeholder, str(value))
            return {
                "success": True,
                "rendered_prompt": rendered,
                "original_prompt": prompt_content,
                "variables_used": list(variables.keys()) if variables else [],
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "prompt_rendering_failed",
            }

    def validate_prompt(self, prompt_name: str) -> Dict[str, Any]:
        """
        Validate a prompt's content.
        Args:
            prompt_name: Name of the prompt to validate
        Returns:
            Dictionary with validation result
        """
        get_result = self.get_prompt(prompt_name)
        if not get_result["success"]:
            return get_result
        prompt_content = get_result["prompt"]
        # Basic validation checks
        issues = []
        if len(prompt_content) < 20:
            issues.append("Prompt is too short (should be at least 20 characters)")
        if len(prompt_content) > 10000:
            issues.append("Prompt is too long (should be less than 10,000 characters)")
        if not prompt_content.strip():
            issues.append("Prompt is empty or contains only whitespace")
        if issues:
            return {
                "success": False,
                "issues": issues,
                "error_class": "prompt_validation_failed",
            }
        return {
            "success": True,
            "message": "Prompt is valid",
            "character_count": len(prompt_content),
            "word_count": len(prompt_content.split()),
        }

    def get_prompt_stats(self) -> Dict[str, Any]:
        """Get statistics about prompts."""
        try:
            stats: Dict[str, Any] = {
                "total_prompts": len(self.prompt_cache),
                "cached_prompts": len(self.prompt_cache),
                "prompt_files": [],
            }
            for filename in os.listdir(self.prompts_dir):
                if filename.endswith(".txt"):
                    prompt_path = os.path.join(self.prompts_dir, filename)
                    file_size = os.path.getsize(prompt_path)
                    stats["prompt_files"].append(
                        {
                            "name": filename,
                            "size_bytes": file_size,
                            "cached": filename[:-4] in self.prompt_cache,
                        }
                    )
            return {"success": True, "stats": stats}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_class": "stats_retrieval_failed",
            }

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message with prompt manager context."""
        context = {
            "component": "prompt_manager",
            "cached_prompts": len(self.prompt_cache),
        }
        if level == "info":
            logger.info(message, extra=context)
        elif level == "warning":
            logger.warning(message, extra=context)
        elif level == "error":
            logger.error(message, extra=context)
        else:
            logger.debug(message, extra=context)


# Example usage


def create_prompt_manager() -> PromptManager:
    """Create a prompt manager instance."""
    return PromptManager()


def get_clarify_prompt() -> Dict[str, Any]:
    """Get the clarify prompt."""
    manager = create_prompt_manager()
    return manager.get_prompt("clarify_system")


def get_generator_prompt() -> Dict[str, Any]:
    """Get the generator prompt."""
    manager = create_prompt_manager()
    return manager.get_prompt("generator_system")
