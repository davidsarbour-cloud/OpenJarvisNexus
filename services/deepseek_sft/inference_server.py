"""
Serveur d'inférence FastAPI pour NOVA (deepseek-r1:7b ou fine-tuned).
Proxy vers Ollama avec parsing du chain-of-thought <think>...</think>.

Démarrage : uvicorn inference_server:app --host 0.0.0.0 --port 9000
"""

import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

app = FastAPI(title="NOVA Inference Server", version="1.0.0")

OLLAMA_HOST    = os.getenv("OLLAMA_HOST",    "http://localhost:11434")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-r1:7b")

NOVA_SYSTEM = (
    "Tu es NOVA, agent de raisonnement Nexus9. "
    "Tu génères du code Python, FastAPI, TypeScript complet et fonctionnel. "
    "Tu raisonnes étape par étape. "
    "Stack : Python 3.11, FastAPI, React 19, Docker, Ollama. "
    "Réponds en français sauf si on te demande l'anglais."
)


class InferRequest(BaseModel):
    prompt: str
    model: str = DEEPSEEK_MODEL
    temperature: float = 0.1
    max_tokens: int = 2048
    system: str = NOVA_SYSTEM


class PipelineRequest(BaseModel):
    steps: list[str]
    model: str = DEEPSEEK_MODEL


def parse_think(content: str) -> dict:
    """Sépare le bloc <think> de la réponse finale."""
    think, answer = "", content
    if "<think>" in content and "</think>" in content:
        think  = content.split("<think>")[1].split("</think>")[0].strip()
        answer = content.split("</think>")[-1].strip()
    return {"think": think, "answer": answer}


@app.post("/nova/infer")
async def nova_infer(req: InferRequest):
    """Inférence simple avec parsing chain-of-thought."""
    messages = [
        {"role": "system",  "content": req.system},
        {"role": "user",    "content": req.prompt},
    ]
    async with httpx.AsyncClient(timeout=120) as client:
        try:
            r = await client.post(
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model":    req.model,
                    "messages": messages,
                    "stream":   False,
                    "options":  {"temperature": req.temperature, "num_predict": req.max_tokens},
                },
            )
            r.raise_for_status()
        except Exception as e:
            raise HTTPException(503, f"Ollama indisponible: {e}")

    content = r.json().get("message", {}).get("content", "")
    parsed  = parse_think(content)
    return {"model": req.model, **parsed}


@app.post("/nova/code")
async def nova_code(req: InferRequest):
    """Génération de code — température basse, system spécialisé."""
    req.system = (
        "Tu es NOVA, expert en code Python et FastAPI. "
        "Tu écris TOUJOURS du code complet, jamais de '...'. "
        "Tu commentes en français. "
        "Tu retournes UNIQUEMENT le code dans un bloc ```python."
    )
    req.temperature = 0.05
    return await nova_infer(req)


@app.post("/nova/pipeline")
async def nova_pipeline(req: PipelineRequest):
    """Pipeline multi-étapes — chaque résultat alimente l'étape suivante."""
    results = []
    context = ""
    for i, step in enumerate(req.steps):
        prompt = f"Étape {i+1}/{len(req.steps)}: {step}"
        if context:
            prompt += f"\n\nRésultat étape précédente:\n{context}"
        infer_req = InferRequest(prompt=prompt, model=req.model)
        response  = await nova_infer(infer_req)
        context   = response["answer"]
        results.append({"step": i + 1, "task": step, **response})
    return {"pipeline": results, "final_output": context}


@app.get("/nova/models")
async def list_models():
    """Liste les modèles Ollama disponibles."""
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            r = await client.get(f"{OLLAMA_HOST}/api/tags")
            return {"models": [m["name"] for m in r.json().get("models", [])]}
        except Exception:
            return {"models": [], "error": "Ollama indisponible"}


@app.get("/health")
async def health():
    return {"status": "ok", "model": DEEPSEEK_MODEL, "ollama": OLLAMA_HOST}
