"""Verify one bounded coding answer over loopback without executing model output."""
import ast
import json
import time
from http.client import HTTPConnection

started = time.monotonic()
conn = HTTPConnection("127.0.0.1", 18080, timeout=180)
question = ("Fix this Python expression to return the smaller of a and b: max(a,b). "
            "Use a single built-in function. Reply only with the corrected expression.")
payload = {"model": "qwen2.5-coder-3b", "messages": [{"role": "user", "content": question}],
           "temperature": 0, "max_tokens": 32, "stream": False}
try:
    conn.request("POST", "/v1/chat/completions", json.dumps(payload), {"Content-Type": "application/json"})
    response = conn.getresponse()
    if response.status != 200:
        raise SystemExit(f"Local model HTTP {response.status}")
    answer = json.loads(response.read(65536))["choices"][0]["message"]["content"].strip()
finally:
    conn.close()
lines = answer.splitlines()
if len(lines) >= 3 and lines[0] in {"```", "```python"} and lines[-1] == "```":
    answer = "\n".join(lines[1:-1])
tree = ast.dump(ast.parse(answer.strip("` "), mode="eval"))
if tree not in {ast.dump(ast.parse(expr, mode="eval")) for expr in ("min(a,b)", "min(b,a)")}:
    raise SystemExit("Local answer received, but coding check did not match.")
print(f"PASS: local model corrected the expression in {time.monotonic()-started:.1f}s")
