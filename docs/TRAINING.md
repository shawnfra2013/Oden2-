# Offline candidate adapter training

The handheld serves the quantized Qwen2.5-Coder-3B-Instruct GGUF. Use a separate training computer with the matching upstream Transformers-format safetensors checkpoint and its tokenizer. Check the upstream Qwen Research License for your use. The training process needs PyTorch, Transformers (4.x) and PEFT. The script uses float32 weights and one example per step. Provision memory for the base weights (about 12 GB for 3 billion float32 parameters), activations, the runtime and the adapter. GPU acceleration is optional. Use local storage for private examples.

Keep two JSONL files. Each line has a question, the reviewed correct answer and a boolean approved field. Keep real user files, scraped websites and receipt text out of both files unless individually selected and reviewed. Put new tasks in the held-out file before training. A sample schema is `{"question":"...","answer":"...","approved":true}`.

    python scripts/train_adapter.py --train reviewed.jsonl --holdout heldout.jsonl --base /models/qwen-base --output /models/odin-candidate --check-data

Remove the final flag for one training epoch. The base and examples stay local. The script writes the adapter and baseline/candidate held-out answer loss into a new directory. Inspect task correctness separately. A lower loss alone does not establish better code. Test a compatible converted GGUF adapter against the original on the handheld, including correctness, memory and latency, before promoting it. The training command has no mailbox trigger, deployment or Git push.

The software can prepare and evaluate a candidate with reviewed data. Autonomous labeling, continuous self-training and automatic activation are outside the current release.

## Practice and progress notes

Run `python -B scripts/odin_practice.py --next` on Odin for one local exercise and `python -B scripts/odin_practice.py` to read the notebook offline. The private GitHub mailbox accepts the same bounded action, `practice_next`. Both interfaces share nine cases and one persistent SQLite notebook in the Termux user's home. One request claims at most one case. A claimed case interrupted before its result was saved stays ungraded. An exhausted set stops without contacting the model.

The notebook records the question, reference, expected and actual answer, timing and outcome. Two distinct incorrect responses in the same skill flag it for diagnosis. Transport failures and interrupted jobs do not count as model mistakes. Check retrieval, prompts and grading before attributing a pattern to the weights. If the pattern persists on new examples, train a separate candidate with reviewed corrections and measure held-out correctness and regressions before promotion. These nine published exercises remain practice material.

On the local UI, open Tasks → Practice notebook to read the results. After a miss, the next case of the same kind includes a brief, fixed reminder about how to approach it.

## Targeted retests

The four `practice_followup` cases use their own local notebook and receipt IDs. First ask a new failed-check question and a UTF-8 byte-count question without coaching. Then use new inputs with a condition-matching cue or a UTF-8 range reference. A supported correct answer measures use of the supplied evidence. These items are public practice materials, unsuitable as blind promotion tests. Select Targeted retests in the practice notebook or run `python -B scripts/odin_practice.py --followup` to read them. Add `--next` to run one.

The notebook recalculates reviewed totals from saved answers. Workflow action words ignore capitalization during review. File and expression answers retain exact grading. Raw receipt results remain available for comparison.
