# Offline candidate adapter training

The handheld serves the quantized Qwen2.5-Coder-3B-Instruct GGUF. Use a separate training computer with the matching upstream Transformers-format safetensors checkpoint and its tokenizer. Check the upstream Qwen Research License for your use. The training process needs PyTorch, Transformers (4.x) and PEFT. The script uses float32 weights and one example per step. Provision memory for the base weights (about 12 GB for 3 billion float32 parameters), activations, the runtime and the adapter. GPU acceleration is optional. Use local storage for private examples.

Keep two JSONL files. Each line has a question, the reviewed correct answer and a boolean approved field. Keep real user files, scraped websites and receipt text out of both files unless individually selected and reviewed. Put new tasks in the held-out file before training. A sample schema is `{"question":"...","answer":"...","approved":true}`.

    python scripts/train_adapter.py --train reviewed.jsonl --holdout heldout.jsonl --base /models/qwen-base --output /models/odin-candidate --check-data

Remove the final flag for one training epoch. The base and examples stay local. The script writes the adapter and baseline/candidate held-out answer loss into a new directory. Inspect task correctness separately. A lower loss alone does not establish better code. Test a compatible converted GGUF adapter against the original on the handheld, including correctness, memory and latency, before promoting it. The training command has no mailbox trigger, deployment or Git push.

The software can prepare and evaluate a candidate with reviewed data. Autonomous labeling, continuous self-training and automatic activation are outside the current release.
