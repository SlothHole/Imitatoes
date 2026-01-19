# Imitatoes

Build a ComfyUI “self-improving” workflow where each render is evaluated by a local vision LLM, which then edits the prompt/parameters and triggers another run. The loop repeats automatically—generate → critique → adjust → regenerate—until the model returns a done verdict or a max-iteration, producing a final image that matches a defined goal spec.

## Custom node

The `ImitatoesSelfImprovingPrompt` node helps manage the text-loop portion of the workflow by appending critique text to the prompt and signaling whether another iteration should run.

1. Copy the `custom_nodes/imitatoes` folder into your ComfyUI `custom_nodes` directory.
2. Restart ComfyUI and add **Imitatoes Self-Improving Prompt** from the **Imitatoes** category.
3. Feed the `prompt_out` into your main text encoder or prompt node, and use `should_continue`/`next_iteration` to control loop logic.

## Workflow

Import `workflows/imitatoes_self_improving.json` to see a starter loop that showcases the node outputs.
