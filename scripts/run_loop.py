#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class LoopConfig:
    workflow_path: Path
    prompt: str
    negative_prompt: str
    cfg: float | None
    steps: int | None
    seed: int | None
    iterations_per_loop: int
    max_loops: int
    comfy_url: str
    ollama_url: str
    ollama_model: str
    output_dir: Path
    poll_interval_s: float
    poll_timeout_s: float
    done_token: str


def parse_args() -> LoopConfig:
    parser = argparse.ArgumentParser(description="Run the Imitatoes self-improving loop.")
    parser.add_argument("--workflow", type=Path, required=True, help="Path to the ComfyUI API workflow JSON.")
    parser.add_argument("--prompt", required=True, help="Base prompt text.")
    parser.add_argument("--negative-prompt", default="", help="Negative prompt text.")
    parser.add_argument("--cfg", type=float, default=None, help="Override CFG scale.")
    parser.add_argument("--steps", type=int, default=None, help="Override step count.")
    parser.add_argument("--seed", type=int, default=None, help="Override seed.")
    parser.add_argument("--iterations-per-loop", type=int, default=1, help="Generate/review iterations per loop.")
    parser.add_argument("--max-loops", type=int, default=3, help="Maximum loops to attempt.")
    parser.add_argument("--comfy-url", default="http://127.0.0.1:8188", help="ComfyUI base URL.")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434", help="Ollama base URL.")
    parser.add_argument("--ollama-model", default="llava-llama3", help="Ollama vision model.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("runs"),
        help="Directory to store images and critique logs.",
    )
    parser.add_argument("--poll-interval", type=float, default=2.0, help="Seconds between history polls.")
    parser.add_argument("--poll-timeout", type=float, default=180.0, help="Timeout for ComfyUI job completion.")
    parser.add_argument("--done-token", default="[DONE]", help="Token that signals completion.")
    args = parser.parse_args()
    return LoopConfig(
        workflow_path=args.workflow,
        prompt=args.prompt,
        negative_prompt=args.negative_prompt,
        cfg=args.cfg,
        steps=args.steps,
        seed=args.seed,
        iterations_per_loop=args.iterations_per_loop,
        max_loops=args.max_loops,
        comfy_url=args.comfy_url.rstrip("/"),
        ollama_url=args.ollama_url.rstrip("/"),
        ollama_model=args.ollama_model,
        output_dir=args.output_dir,
        poll_interval_s=args.poll_interval,
        poll_timeout_s=args.poll_timeout,
        done_token=args.done_token,
    )


def load_workflow(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def replace_tokens(payload: Any, replacements: dict[str, str]) -> Any:
    if isinstance(payload, dict):
        return {key: replace_tokens(value, replacements) for key, value in payload.items()}
    if isinstance(payload, list):
        return [replace_tokens(value, replacements) for value in payload]
    if isinstance(payload, str):
        updated = payload
        for token, value in replacements.items():
            updated = updated.replace(token, value)
        return updated
    return payload


def request_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def request_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def submit_prompt(config: LoopConfig, workflow: dict[str, Any]) -> str:
    payload = {"prompt": workflow}
    response = request_json(f"{config.comfy_url}/prompt", payload)
    return response["prompt_id"]


def wait_for_history(config: LoopConfig, prompt_id: str) -> dict[str, Any]:
    deadline = time.time() + config.poll_timeout_s
    while time.time() < deadline:
        history = request_json(f"{config.comfy_url}/history/{prompt_id}")
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(config.poll_interval_s)
    raise TimeoutError("Timed out waiting for ComfyUI history.")


def extract_first_image(history: dict[str, Any]) -> dict[str, str]:
    outputs = history.get("outputs", {})
    for node_data in outputs.values():
        images = node_data.get("images", [])
        if images:
            return images[0]
    raise ValueError("No images found in ComfyUI history outputs.")


def download_image(config: LoopConfig, image_info: dict[str, str]) -> bytes:
    params = urllib.parse.urlencode(
        {
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        }
    )
    return request_bytes(f"{config.comfy_url}/view?{params}")


def build_ollama_payload(config: LoopConfig, prompt: str, negative_prompt: str, image_b64: str) -> dict[str, Any]:
    system_prompt = (
        "You are a vision critic. Return ONLY valid JSON matching this schema:\n"
        "{\n"
        '  "done": true|false,\n'
        '  "changes": {\n'
        '    "prompt_append": string,\n'
        '    "neg_append": string,\n'
        '    "cfg": number|null,\n'
        '    "steps": number|null,\n'
        '    "seed": number|string|null\n'
        "  },\n"
        '  "reason": "short"\n'
        "}\n"
        f'Use "{config.done_token}" in the reason if the goal is satisfied.'
    )
    return {
        "model": config.ollama_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Prompt:\n{prompt}\n\nNegative:\n{negative_prompt}\n\nReview the image.",
                "images": [image_b64],
            },
        ],
    }


def extract_json_blob(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in response.")
    return json.loads(text[start : end + 1])


def apply_changes(
    prompt: str, negative_prompt: str, cfg: float | None, steps: int | None, seed: int | None, changes: dict[str, Any]
) -> tuple[str, str, float | None, int | None, int | None]:
    prompt_append = changes.get("prompt_append") or ""
    neg_append = changes.get("neg_append") or ""
    new_prompt = f"{prompt}\n{prompt_append}".strip() if prompt_append else prompt
    new_negative = f"{negative_prompt}\n{neg_append}".strip() if neg_append else negative_prompt
    new_cfg = cfg if changes.get("cfg") is None else float(changes["cfg"])
    new_steps = steps if changes.get("steps") is None else int(changes["steps"])
    new_seed = seed
    seed_change = changes.get("seed")
    if isinstance(seed_change, int):
        new_seed = seed_change
    elif isinstance(seed_change, str) and seed_change.isdigit():
        new_seed = int(seed_change)
    return new_prompt, new_negative, new_cfg, new_steps, new_seed


def save_iteration(output_dir: Path, loop_index: int, iteration_index: int, image_bytes: bytes, critique: dict[str, Any]):
    output_dir.mkdir(parents=True, exist_ok=True)
    image_path = output_dir / f"loop_{loop_index:02d}_iter_{iteration_index:02d}.png"
    image_path.write_bytes(image_bytes)
    critique_path = output_dir / f"loop_{loop_index:02d}_iter_{iteration_index:02d}.json"
    critique_path.write_text(json.dumps(critique, indent=2), encoding="utf-8")


def wait_for_instruction() -> None:
    if sys.stdin.isatty():
        input("Completed early. Press Enter to exit and await further instruction.")


def run_loop(config: LoopConfig) -> None:
    workflow = load_workflow(config.workflow_path)
    current_prompt = config.prompt
    current_negative = config.negative_prompt
    current_cfg = config.cfg
    current_steps = config.steps
    current_seed = config.seed
    for loop_index in range(1, config.max_loops + 1):
        for iteration_index in range(1, config.iterations_per_loop + 1):
            replacements = {
                "__PROMPT__": current_prompt,
                "__NEG__": current_negative,
                "__CFG__": "" if current_cfg is None else str(current_cfg),
                "__STEPS__": "" if current_steps is None else str(current_steps),
                "__SEED__": "" if current_seed is None else str(current_seed),
            }
            workflow_payload = replace_tokens(workflow, replacements)
            prompt_id = submit_prompt(config, workflow_payload)
            history = wait_for_history(config, prompt_id)
            image_info = extract_first_image(history)
            image_bytes = download_image(config, image_info)
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            ollama_payload = build_ollama_payload(config, current_prompt, current_negative, image_b64)
            ollama_response = request_json(f"{config.ollama_url}/api/chat", ollama_payload)
            content = ollama_response.get("message", {}).get("content", "")
            critique = extract_json_blob(content)
            save_iteration(config.output_dir, loop_index, iteration_index, image_bytes, critique)
            done = bool(critique.get("done"))
            if done:
                wait_for_instruction()
                return
            changes = critique.get("changes", {})
            current_prompt, current_negative, current_cfg, current_steps, current_seed = apply_changes(
                current_prompt, current_negative, current_cfg, current_steps, current_seed, changes
            )
    print("Reached max loops without early completion.")


def main() -> None:
    config = parse_args()
    run_loop(config)


if __name__ == "__main__":
    main()
