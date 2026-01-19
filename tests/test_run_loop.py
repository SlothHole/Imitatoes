import json

import scripts.run_loop as run_loop


def test_apply_changes_updates_fields():
    prompt, negative, cfg, steps, seed = run_loop.apply_changes(
        "base",
        "neg",
        4.5,
        20,
        42,
        {
            "prompt_append": "extra",
            "neg_append": "avoid",
            "cfg": 7,
            "steps": 30,
            "seed": "123",
        },
    )

    assert prompt == "base\nextra"
    assert negative == "neg\navoid"
    assert cfg == 7.0
    assert steps == 30
    assert seed == 123


def test_run_loop_stops_on_done(tmp_path, monkeypatch):
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text(json.dumps({"prompt": "__PROMPT__"}), encoding="utf-8")

    responses = {
        "prompt": {"prompt_id": "abc"},
        "history": {
            "abc": {
                "outputs": {
                    "node": {
                        "images": [
                            {
                                "filename": "image.png",
                                "subfolder": "",
                                "type": "output",
                            }
                        ]
                    }
                }
            }
        },
        "chat": {
            "message": {
                "content": json.dumps(
                    {
                        "done": True,
                        "changes": {
                            "prompt_append": "",
                            "neg_append": "",
                            "cfg": None,
                            "steps": None,
                            "seed": "keep",
                        },
                        "reason": "[DONE] looks good",
                    }
                )
            }
        },
    }

    def fake_request_json(url, payload=None):
        if url.endswith("/prompt"):
            return responses["prompt"]
        if "/history/" in url:
            return responses["history"]
        if url.endswith("/api/chat"):
            return responses["chat"]
        raise AssertionError(f"Unexpected URL {url}")

    def fake_request_bytes(url):
        assert url.startswith("http://127.0.0.1:8188/view?")
        return b"fake-image"

    monkeypatch.setattr(run_loop, "request_json", fake_request_json)
    monkeypatch.setattr(run_loop, "request_bytes", fake_request_bytes)
    monkeypatch.setattr(run_loop, "wait_for_instruction", lambda: None)

    config = run_loop.LoopConfig(
        workflow_path=workflow_path,
        prompt="base prompt",
        negative_prompt="",
        cfg=None,
        steps=None,
        seed=None,
        iterations_per_loop=1,
        max_loops=2,
        comfy_url="http://127.0.0.1:8188",
        ollama_url="http://127.0.0.1:11434",
        ollama_model="llava-llama3",
        output_dir=tmp_path / "runs",
        poll_interval_s=0.0,
        poll_timeout_s=1.0,
        done_token="[DONE]",
    )

    run_loop.run_loop(config)

    image_path = config.output_dir / "loop_01_iter_01.png"
    critique_path = config.output_dir / "loop_01_iter_01.json"
    assert image_path.exists()
    assert critique_path.exists()
