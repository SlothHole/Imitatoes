from pathlib import Path


def test_repository_has_readme() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    assert (repo_root / "README.md").is_file()
