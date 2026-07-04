import json
import re
import subprocess


def parse_json(text: str):
    """
    Extracts JSON from an LLM response, even if wrapped in markdown.
    """

    text = text.strip()

    # Remove ```json ... ```
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    # Find first JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return json.loads(match.group())

    raise ValueError("No valid JSON found.")


async def chat(messages, model="gpt-4o", max_tokens=1500):
    """
    Uses Simon Willison's llm CLI.
    """

    prompt = "\n\n".join(
        f"{m['role'].upper()}:\n{m['content']}"
        for m in messages
    )

    cmd = [
        "llm",
        "-m",
        model,
        prompt,
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr)

    return proc.stdout.strip()
