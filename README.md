# Imitatoes
Build a ComfyUI “self-improving” workflow where each render is evaluated by a local vision LLM, which then edits the prompt/parameters and triggers another run. The loop repeats automatically—generate → critique → adjust → regenerate—until the model returns a done verdict or a max-iteration, producing a final image that matches a defined goal spec.

## Quick start
1. Install tooling and set up the virtual environment:
   ```bash
   ./scripts/install.sh
   source .venv/bin/activate
   ```
2. Run the smoke test stack:
   ```bash
   ./scripts/test.sh
   ```
