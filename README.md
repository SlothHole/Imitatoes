# Imitatoes

Build a ComfyUI “self-improving” workflow where each render is evaluated by a local vision LLM, which then edits the prompt/parameters and triggers another run. The loop repeats automatically—generate → critique → adjust → regenerate—until the model returns a done verdict or a max-iteration, producing a final image that matches a defined goal spec.

## Custom node

The `ImitatoesSelfImprovingPrompt` node helps manage the text-loop portion of the workflow by appending critique text to the prompt and signaling whether another iteration should run.

1. Copy the `custom_nodes/imitatoes` folder into your ComfyUI `custom_nodes` directory.
2. Restart ComfyUI and add **Imitatoes Self-Improving Prompt** from the **Imitatoes** category.
3. Feed the `prompt_out` into your main text encoder or prompt node, and use `should_continue`/`next_iteration` to control loop logic.

## Workflow

Import `workflows/imitatoes_self_improving.json` to see a starter loop that showcases the node outputs.
## Goal

Create an external orchestration loop that drives ComfyUI’s API and a local vision model (via Ollama) to iteratively refine images until a clear done condition is met.

## Phase 0 — Define the stop condition

Pick a primary done rule (with a hard safety cap) to prevent endless loops.

Recommended:

* Model returns JSON with `done: true` when satisfied.
* Hard cap: `max_iters = 5–10`.

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

## Phase 3 — Build the controller loop (PowerShell)

The controller should:

1. Load the workflow template JSON.
2. Replace tokens with the current prompt/params.
3. `POST /prompt` to ComfyUI.
4. Poll `/history/{prompt_id}` until outputs exist.
5. Download the image via `/view`.
6. Send the image + context to Ollama `/api/chat` as base64.
7. Parse the JSON response and apply patches.
8. Stop on `done` or `max_iters`.

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

* `iter_01.png` / `iter_01.jpg`
* `iter_01.json` (LLM response)
* `iter_01_patch.json` (applied changes)

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
* ✅ PowerShell loop controller calling `/prompt`, `/history`, `/view`, `/api/chat`
* ✅ Iteration logs + saved images per step
* ✅ Written goal spec defining “happy”
