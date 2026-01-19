# Imitatoes

Build a ComfyUI “self-improving” workflow where each render is evaluated by a local vision LLM, which then edits the prompt/parameters and triggers another run. The loop repeats automatically—generate → critique → adjust → regenerate—until the model returns a done verdict or a max-iteration, producing a final image that matches a defined goal spec.

## Custom node

The `ImitatoesSelfImprovingPrompt` node helps manage the text-loop portion of the workflow by appending critique text to the prompt and signaling whether another iteration should run.

1. Copy the `custom_nodes/imitatoes` folder into your ComfyUI `custom_nodes` directory.
2. Restart ComfyUI and add **Imitatoes Self-Improving Prompt** from the **Imitatoes** category.
3. Feed the `prompt_out` into your main text encoder or prompt node, and use `should_continue`/`next_iteration` to control loop logic.

## Workflow

Import `workflows/imitatoes_self_improving.json` to see a starter loop that showcases the node outputs.

## Setup

Prerequisites:

* Python 3 (for the automation scripts and tests)
* ComfyUI (for the custom node)

Run the install script to create a local virtual environment and install dependencies from `requirements.txt` and `requirements-dev.txt`:

```bash
./scripts/install.sh
```

Activate the virtual environment before running scripts:

```bash
source .venv/bin/activate
```

## Run/Validate

Use the test script to run ruff and pytest:

```bash
./scripts/test.sh
```

## Goal

Run an external orchestration loop that drives ComfyUI’s API and a local vision model (via Ollama) to iteratively refine images until the model confirms the requirements are met or the maximum loop count is reached.

## Loop behavior

* The user sets **iterations per loop**, which controls how many times the system generates → reviews → regenerates within a single loop.
* The user also sets a **max loops** value to cap how many loops can run.
* If the vision model marks the output as complete, the loop ends early and waits for further instruction.

## Phase 1 — Install and verify the local vision model (Ollama)

1. Install Ollama and confirm the service is running.
2. Verify the API: `http://127.0.0.1:11434`.
3. Pull a vision model:
   * `ollama pull llava-llama3` (fast/capable default)
   * Optional: `Qwen2.5-VL` for stronger vision reasoning
4. Ensure the vision API supports base64 images in the `images` array.

## Phase 2 — Prepare the ComfyUI workflow for patching

1. Build a normal, stable workflow in ComfyUI (no loop nodes).
2. Export the workflow in **API format** (the `/prompt` JSON graph).
3. Add placeholder tokens where edits will happen:
   * Positive prompt: `__PROMPT__`
   * Negative prompt: `__NEG__`
   * Optional: `__CFG__`, `__STEPS__`, `__SEED__`
4. Confirm outputs are retrievable via `/history/{prompt_id}` and `/view`.

## Phase 3 — Run the controller loop (Python)

Use the Python controller to orchestrate ComfyUI and Ollama:

```bash
python scripts/run_loop.py \
  --workflow workflows/imitatoes_self_improving.json \
  --prompt "your prompt" \
  --negative-prompt "your negatives" \
  --iterations-per-loop 2 \
  --max-loops 5
```

The controller will:

1. Load the workflow template JSON.
2. Replace tokens with the current prompt/params.
3. `POST /prompt` to ComfyUI.
4. Poll `/history/{prompt_id}` until outputs exist.
5. Download the image via `/view`.
6. Send the image + context to Ollama `/api/chat` as base64.
7. Parse the JSON response and apply patches.
8. Stop on `done` or when the loop limits are reached.

### Required LLM response (JSON only)

```
{
  "done": true,
  "changes": {
    "prompt_append": "",
    "neg_append": "",
    "cfg": null,
    "steps": null,
    "seed": "keep"
  },
  "reason": "short"
}
```

## Phase 4 — Image size guardrail

To keep payloads small and fast:

* Resize longest edge to ~768–1024px.
* Encode as JPEG quality ~85 (unless lossless is needed).

## Phase 5 — Logging and traceability

Create a run folder per session and save:

* `loop_01_iter_01.png`
* `loop_01_iter_01.json` (LLM response)

This provides visibility into oscillations, seed changes, and prompt bloat.

## Phase 6 — Tuning the agent behavior

* Keep edits small and targeted.
* Control seed policy (stable unless composition is wrong).
* Avoid negative prompt explosion; add only what’s visible.
* Optionally compare previous vs current and revert regressions.

## Optional: in-graph loops (less recommended)

You can embed loops with:

* ControlFlowUtils
* ComfyUI-Easy-Use `whileLoopEnd`
* `comfyui-ollama` nodes

External orchestration is more robust.

## Deliverables checklist

* ✅ Ollama installed + vision model pulled
* ✅ ComfyUI workflow exported with `__PROMPT__` / `__NEG__`
* ✅ Python loop controller calling `/prompt`, `/history`, `/view`, `/api/chat`
* ✅ Iteration logs + saved images per step
* ✅ Written goal spec defining “happy”
