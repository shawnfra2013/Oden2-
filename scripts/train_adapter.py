"""Train a separate candidate adapter from reviewed local examples, without network access."""
import argparse
import json
import math
import os
from pathlib import Path
import tempfile


def examples(path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("approved") is not True:
            raise ValueError("Each example needs explicit review")
        pair = tuple(row.get(k) for k in ("question", "answer"))
        if not all(isinstance(v, str) and 0 < len(v.strip()) <= 6000 for v in pair):
            raise ValueError("Invalid question or answer")
        rows.append(pair)
    if not rows:
        raise ValueError("Empty example file")
    return rows


def validate(train, holdout):
    keys = [" ".join(q.casefold().split()) for q, _ in train + holdout]
    if len(keys) != len(set(keys)):
        raise ValueError("Repeated question within or across datasets")


def run(args, train, holdout, output):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(42)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(args.base, local_files_only=True, trust_remote_code=False)
    model = AutoModelForCausalLM.from_pretrained(args.base, local_files_only=True,
                                                 trust_remote_code=False, use_safetensors=True,
                                                 torch_dtype=torch.float32)
    if model.config.model_type != "qwen2":
        raise ValueError("Expected the Qwen2 architecture")
    model.to(device)
    model.config.use_cache = False

    def prepare(pair):
        q, a = pair
        turns = [{"role": "user", "content": q}]
        prompt = tok.apply_chat_template(turns, tokenize=True, add_generation_prompt=True)
        full = tok.apply_chat_template(turns + [{"role": "assistant", "content": a}], tokenize=True)
        if full[:len(prompt)] != prompt or len(full) <= len(prompt) or len(full) > 512:
            raise ValueError("Template mismatch or example exceeds 512 tokens")
        ids = torch.tensor([full], device=device)
        labels = ids.clone()
        labels[:, :len(prompt)] = -100
        return ids, labels

    train_batches = [prepare(p) for p in train]
    eval_batches = [prepare(p) for p in holdout]

    def heldout_loss():
        model.eval()
        with torch.no_grad():
            scores = [model(input_ids=x, labels=y).loss.item() for x, y in eval_batches]
        result = sum(scores) / len(scores)
        if not math.isfinite(result):
            raise ValueError("Nonfinite evaluation loss")
        return result

    baseline = heldout_loss()
    model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, target_modules=["q_proj", "v_proj"],
                                             task_type="CAUSAL_LM", lora_dropout=0.0))
    model.train()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=0.0001)
    for ids, labels in train_batches:
        optimizer.zero_grad(set_to_none=True)
        loss = model(input_ids=ids, labels=labels).loss
        if not torch.isfinite(loss).item():
            raise ValueError("Nonfinite training loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    score = heldout_loss()
    model.save_pretrained(output, safe_serialization=True)
    report = {"train_examples": len(train), "holdout_examples": len(holdout),
              "baseline_mean_answer_loss": baseline, "candidate_mean_answer_loss": score,
              "device": device, "promotion": "requires separate evaluation and review"}
    (output / "evaluation.json").write_text(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("train", "holdout", "base", "output"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--check-data", action="store_true")
    args = parser.parse_args()
    train, holdout = examples(args.train), examples(args.holdout)
    validate(train, holdout)
    if args.check_data:
        print(f"Validated {len(train)} training and {len(holdout)} held-out examples")
        return
    if not args.base.is_dir() or args.output.exists():
        parser.error("Supply a local base checkpoint and a new candidate directory")
    os.environ["HF_HUB_OFFLINE"] = "1"
    with tempfile.TemporaryDirectory(dir=args.output.parent) as scratch:
        adapter = Path(scratch) / "adapter"
        run(args, train, holdout, adapter)
        adapter.rename(args.output)


if __name__ == "__main__":
    main()
