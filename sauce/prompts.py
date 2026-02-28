from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text().strip()


THINKING_PROMPT = _load("thinking_v4.md")
CODE_PROMPT = _load("code.md")
TEST_PROMPT = _load("test_v2.md")
