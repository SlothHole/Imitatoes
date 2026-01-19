"""Custom node for a simple self-improving prompt loop in ComfyUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LoopResult:
    prompt: str
    should_continue: bool
    iteration: int


class ImitatoesSelfImprovingPrompt:
    """Create a revised prompt based on critique text and loop settings."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True}),
                "critique": ("STRING", {"multiline": True, "default": ""}),
                "iteration": ("INT", {"default": 1, "min": 1, "max": 100}),
                "max_iterations": ("INT", {"default": 5, "min": 1, "max": 100}),
                "done_token": ("STRING", {"default": "[DONE]"}),
            }
        }

    RETURN_TYPES = ("STRING", "BOOLEAN", "INT")
    RETURN_NAMES = ("prompt_out", "should_continue", "next_iteration")
    FUNCTION = "apply_critique"
    CATEGORY = "Imitatoes"

    def apply_critique(
        self,
        prompt: str,
        critique: str,
        iteration: int,
        max_iterations: int,
        done_token: str,
    ):
        result = self._build_result(prompt, critique, iteration, max_iterations, done_token)
        return result.prompt, result.should_continue, result.iteration

    @staticmethod
    def _build_result(
        prompt: str,
        critique: str,
        iteration: int,
        max_iterations: int,
        done_token: str,
    ) -> LoopResult:
        has_done_token = done_token.strip() and done_token in critique
        should_continue = iteration < max_iterations and not has_done_token
        if critique.strip():
            updated_prompt = f"{prompt}\n\nCritique:\n{critique.strip()}"
        else:
            updated_prompt = prompt
        return LoopResult(
            prompt=updated_prompt,
            should_continue=should_continue,
            iteration=iteration + 1 if should_continue else iteration,
        )


NODE_CLASS_MAPPINGS = {
    "ImitatoesSelfImprovingPrompt": ImitatoesSelfImprovingPrompt,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ImitatoesSelfImprovingPrompt": "Imitatoes Self-Improving Prompt",
}
