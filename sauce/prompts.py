from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load(name: str) -> str:
    return (_PROMPTS_DIR / name).read_text().strip()


THINKING_PROMPT = _load("thinking.md")
CODE_PROMPT = _load("code.md")
TEST_PROMPT = _load("test.md")
