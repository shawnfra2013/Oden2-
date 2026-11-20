"""Offline trainer smoke test with a disposable tiny Qwen2 model; no weights downloaded."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from safetensors.torch import load_file
from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace
from transformers import PreTrainedTokenizerFast, Qwen2Config, Qwen2ForCausalLM

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    base = root / "base"
    vocab = {s: i for i, s in enumerate(["UNK", "user", "assistant", "one", "two", "three", "four"])}
    raw = Tokenizer(WordLevel(vocab, unk_token="UNK"))
    raw.pre_tokenizer = Whitespace()
    tok = PreTrainedTokenizerFast(tokenizer_object=raw, unk_token="UNK")
    tok.chat_template = "{% for m in messages %}{{ m.role }} {{ m.content }} {% endfor %}{% if add_generation_prompt %}assistant {% endif %}"
    tok.save_pretrained(base)
    model = Qwen2ForCausalLM(Qwen2Config(vocab_size=len(vocab), hidden_size=16, intermediate_size=32,
                                         num_hidden_layers=1, num_attention_heads=2, num_key_value_heads=1))
    model.save_pretrained(base)
    for name, q, a in [("train", "one", "two"), ("holdout", "three", "four")]:
        (root / name).write_text(json.dumps(dict(approved=True, question=q, answer=a)))
    out = root / "candidate"
    subprocess.run([sys.executable, "scripts/train_adapter.py", "--train", str(root / "train"),
                    "--holdout", str(root / "holdout"), "--base", str(base), "--output", str(out)], check=True)
    metrics = json.loads((out / "evaluation.json").read_text())
    assert metrics["train_examples"] == metrics["holdout_examples"] == 1
    params = load_file(out / "adapter_model.safetensors")
    assert any("lora_B" in name and tensor.count_nonzero().item() for name, tensor in params.items())
    print("Verified a nonzero adapter weight update and recorded both evaluation losses.")
