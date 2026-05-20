"""
Fine-tuning QLoRA DeepSeek-R1:7B — Nexus9
Optimisé RTX 4070 Super (12 GB VRAM) via Unsloth 4-bit.

Usage :
    python train.py
    python train.py --model deepseek-ai/DeepSeek-R1-Distill-Qwen-7B --epochs 5
"""

import argparse
import os
import json
from datasets import load_dataset

try:
    from unsloth import FastLanguageModel
    UNSLOTH_AVAILABLE = True
except ImportError:
    UNSLOTH_AVAILABLE = False
    print("[WARN] Unsloth non installé — utilisation HuggingFace standard (plus lent)")
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    import torch

from transformers import TrainingArguments
from trl import SFTTrainer

DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "output")

# Modèles compatibles 12 GB VRAM avec QLoRA 4-bit
SUPPORTED_MODELS = {
    "deepseek-r1:7b":    "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
    "deepseek-coder:7b": "deepseek-ai/deepseek-coder-7b-instruct-v1.5",
    "qwen3:7b":          "Qwen/Qwen3-7B",
}

ALPACA_TEMPLATE = (
    "### Instruction:\n{instruction}\n\n"
    "### Input:\n{input}\n\n"
    "### Output:\n{output}"
)


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--model",      default="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
    p.add_argument("--max_seq_len",default=2048,   type=int)
    p.add_argument("--batch_size", default=2,      type=int)
    p.add_argument("--epochs",     default=3,      type=int)
    p.add_argument("--lr",         default=2e-4,   type=float)
    p.add_argument("--lora_r",     default=16,     type=int)
    p.add_argument("--lora_alpha", default=16,     type=int)
    p.add_argument("--output_dir", default=OUTPUT_DIR)
    return p.parse_args()


def load_model_unsloth(model_name: str, max_seq_len: int):
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_len,
        dtype=None,          # auto-détect bfloat16
        load_in_4bit=True,   # QLoRA 4-bit — économise ~6 GB VRAM
    )
    return model, tokenizer


def add_lora(model, lora_r: int, lora_alpha: int):
    return FastLanguageModel.get_peft_model(
        model,
        r=lora_r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=lora_alpha,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=42,
        use_rslora=False,
    )


def formatting_func(example):
    """Formate chaque exemple au format Alpaca."""
    if "text" in example:
        return example["text"]
    return ALPACA_TEMPLATE.format(
        instruction=example.get("instruction", ""),
        input=example.get("input", ""),
        output=example.get("completion", example.get("output", "")),
    )


def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    print(f"[NOVA-SFT] Modèle : {args.model}")
    print(f"[NOVA-SFT] Dataset : {DATASET_DIR}")
    print(f"[NOVA-SFT] Output : {args.output_dir}")
    print(f"[NOVA-SFT] Epochs : {args.epochs} | LR : {args.lr} | Batch : {args.batch_size}")

    # Chargement dataset
    train_path = os.path.join(DATASET_DIR, "train.jsonl")
    valid_path = os.path.join(DATASET_DIR, "valid.jsonl")
    if not os.path.exists(train_path):
        raise FileNotFoundError(f"Lance d'abord: python prepare_dataset.py\n{train_path} introuvable")

    dataset = load_dataset("json", data_files={"train": train_path, "valid": valid_path})

    # Chargement modèle
    if UNSLOTH_AVAILABLE:
        model, tokenizer = load_model_unsloth(args.model, args.max_seq_len)
        model = add_lora(model, args.lora_r, args.lora_alpha)
    else:
        raise RuntimeError("Installe Unsloth: pip install unsloth")

    # Config training — optimisée 4070 Super
    training_args = TrainingArguments(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=4,   # effective batch = batch_size * 4
        warmup_steps=50,
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        fp16=False,
        bf16=True,                        # RTX 4070 Super supporte bfloat16
        logging_steps=50,
        save_strategy="steps",
        save_steps=200,
        evaluation_strategy="steps",
        eval_steps=200,
        load_best_model_at_end=True,
        optim="adamw_8bit",               # Unsloth — économise VRAM
        weight_decay=0.01,
        report_to="none",
        dataloader_num_workers=0,
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset["train"],
        eval_dataset=dataset["valid"],
        dataset_text_field="text",
        formatting_func=formatting_func,
        max_seq_length=args.max_seq_len,
        args=training_args,
        packing=False,
    )

    print("\n[NOVA-SFT] Démarrage du fine-tuning...")
    trainer.train()

    # Sauvegarde LoRA adapter
    adapter_path = os.path.join(args.output_dir, "lora_adapter")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)
    print(f"\n[NOVA-SFT] LoRA adapter sauvegardé → {adapter_path}")

    # Optionnel : merge + export GGUF pour Ollama
    merged_path = os.path.join(args.output_dir, "merged_model")
    print(f"[NOVA-SFT] Pour créer un Modelfile Ollama, lance :")
    print(f"  python export_ollama.py --adapter {adapter_path} --output {merged_path}")


if __name__ == "__main__":
    main()
