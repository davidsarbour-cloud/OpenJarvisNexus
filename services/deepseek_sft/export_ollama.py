"""
Merge LoRA + export GGUF → Modelfile Ollama
Permet de charger le modèle fine-tuned directement dans Ollama.

Usage :
    python export_ollama.py --adapter ./output/lora_adapter --base deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
"""

import argparse
import os
import subprocess

try:
    from unsloth import FastLanguageModel
except ImportError:
    raise RuntimeError("Installe Unsloth: pip install unsloth")


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--adapter",  required=True,  help="Chemin vers le LoRA adapter")
    p.add_argument("--base",     default="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B")
    p.add_argument("--output",   default="./output/nexus9_nova")
    p.add_argument("--quant",    default="q4_k_m", help="Quantification GGUF (q4_k_m, q8_0, f16)")
    p.add_argument("--model_name", default="nexus9-nova", help="Nom dans Ollama")
    return p.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.output, exist_ok=True)

    print(f"[export] Chargement base {args.base} + adapter {args.adapter}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=args.base,
        max_seq_length=2048,
        dtype=None,
        load_in_4bit=True,
    )

    print("[export] Merge LoRA dans le modèle base...")
    model.save_pretrained_merged(args.output, tokenizer, save_method="merged_16bit")

    gguf_path = os.path.join(args.output, f"model-{args.quant}.gguf")
    print(f"[export] Conversion GGUF ({args.quant})...")
    model.save_pretrained_gguf(args.output, tokenizer, quantization_method=args.quant)

    # Modelfile Ollama
    modelfile_content = f"""FROM {gguf_path}

SYSTEM \"\"\"
Tu es NOVA, agent de raisonnement Nexus9.
Tu génères du code Python, FastAPI, TypeScript.
Tu raisonnes étape par étape avant de répondre.
Stack : Python 3.11, FastAPI, React 19, Docker, Ollama.
Réponds en français sauf si on te demande l'anglais.
\"\"\"

PARAMETER temperature 0.1
PARAMETER num_predict 2048
PARAMETER stop "### Instruction:"
PARAMETER stop "### Input:"
"""

    modelfile_path = os.path.join(args.output, "Modelfile")
    with open(modelfile_path, "w") as f:
        f.write(modelfile_content)

    print(f"\n[export] Modelfile créé → {modelfile_path}")
    print(f"\n[export] Pour installer dans Ollama :")
    print(f"  ollama create {args.model_name} -f {modelfile_path}")
    print(f"  ollama run {args.model_name}")
    print(f"\n[export] Dans backend/.env, mettre :")
    print(f"  DEEPSEEK_MODEL={args.model_name}")


if __name__ == "__main__":
    main()
