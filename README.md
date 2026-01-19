# Imitatoes
Build a ComfyUI “self-improving” workflow where each render is evaluated by a local vision LLM, which then edits the prompt/parameters and triggers another run. The loop repeats automatically—generate → critique → adjust → regenerate—until the model returns a done verdict or a max-iteration, producing a final image that matches a defined goal spec
