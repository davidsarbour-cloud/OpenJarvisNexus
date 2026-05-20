"""
Prépare le dataset JSONL pour fine-tuning DeepSeek-R1:7B sur les tâches Nexus9.
Génère train.jsonl / valid.jsonl / test.jsonl dans ./dataset/
"""

import json
import random
import os

DATASET_DIR = os.path.join(os.path.dirname(__file__), "dataset")
os.makedirs(DATASET_DIR, exist_ok=True)

# Template Alpaca — format recommandé pour DeepSeek SFT
TEMPLATE = (
    "### Instruction:\n{instruction}\n\n"
    "### Input:\n{input}\n\n"
    "### Output:\n{output}"
)

# Exemples seed pour Nexus9 (compléter avec tes vrais cas)
SEED_EXAMPLES = [
    {
        "instruction": "Génère un endpoint FastAPI pour le webhook Shopify",
        "input": "Valider la signature HMAC et extraire les événements order/create",
        "output": (
            "from fastapi import APIRouter, Request, HTTPException\n"
            "import hmac, hashlib\n\n"
            "router = APIRouter()\n\n"
            "@router.post('/shopify/webhook')\n"
            "async def shopify_webhook(request: Request):\n"
            "    body = await request.body()\n"
            "    sig = request.headers.get('X-Shopify-Hmac-SHA256', '')\n"
            "    secret = os.getenv('SHOPIFY_SECRET', '').encode()\n"
            "    digest = hmac.new(secret, body, hashlib.sha256).digest()\n"
            "    import base64\n"
            "    if not hmac.compare_digest(base64.b64encode(digest).decode(), sig):\n"
            "        raise HTTPException(403, 'Signature invalide')\n"
            "    event = await request.json()\n"
            "    return {'status': 'ok', 'topic': request.headers.get('X-Shopify-Topic')}\n"
        ),
    },
    {
        "instruction": "Crée un script Python pour uploader un STL sur Etsy",
        "input": "Utiliser l'API Etsy v3, créer un listing digital avec prix en USD",
        "output": (
            "import httpx\n\n"
            "def create_etsy_listing(token: str, shop_id: str, title: str, price: float, stl_path: str):\n"
            "    headers = {'x-api-key': token, 'Content-Type': 'application/json'}\n"
            "    payload = {\n"
            "        'title': title,\n"
            "        'description': f'Fichier STL imprimable 3D — {title}',\n"
            "        'price': price,\n"
            "        'quantity': 999,\n"
            "        'is_digital': True,\n"
            "        'type': 'download',\n"
            "        'who_made': 'i_did',\n"
            "        'when_made': '2020_2024',\n"
            "        'taxonomy_id': 2078,\n"
            "    }\n"
            "    r = httpx.post(f'https://api.etsy.com/v3/application/shops/{shop_id}/listings',\n"
            "                   headers=headers, json=payload)\n"
            "    r.raise_for_status()\n"
            "    return r.json()\n"
        ),
    },
    {
        "instruction": "Écris un agent CrewAI pour la génération de métadonnées Etsy",
        "input": "Générer titre SEO + tags + description pour un produit STL low-poly",
        "output": (
            "from crewai import Agent, Task, Crew\n"
            "from langchain_ollama import ChatOllama\n\n"
            "llm = ChatOllama(model='qwen3:14b', base_url='http://localhost:11434')\n\n"
            "seo_agent = Agent(\n"
            "    role='Expert SEO Etsy',\n"
            "    goal='Générer des métadonnées Etsy optimisées pour la visibilité',\n"
            "    backstory='Spécialiste Etsy avec 5 ans d expérience en impression 3D',\n"
            "    llm=llm,\n"
            ")\n\n"
            "def generate_etsy_metadata(product_name: str, description: str) -> dict:\n"
            "    task = Task(\n"
            "        description=f'Génère titre (max 140 chars), 13 tags, description pour: {product_name}. {description}',\n"
            "        expected_output='JSON avec title, tags[], description',\n"
            "        agent=seo_agent,\n"
            "    )\n"
            "    crew = Crew(agents=[seo_agent], tasks=[task], verbose=False)\n"
            "    return crew.kickoff()\n"
        ),
    },
    {
        "instruction": "Implémenter un pipeline de traitement STL avec trimesh",
        "input": "Charger STL, réparer mesh non-manifold, scale 15cm, exporter",
        "output": (
            "import trimesh\nimport numpy as np\n\n"
            "def process_stl(input_path: str, output_path: str, target_cm: float = 15.0) -> dict:\n"
            "    mesh = trimesh.load(input_path)\n"
            "    if not mesh.is_watertight:\n"
            "        trimesh.repair.fix_normals(mesh)\n"
            "        trimesh.repair.fill_holes(mesh)\n"
            "        trimesh.repair.fix_winding(mesh)\n"
            "    bounds = mesh.bounds\n"
            "    current_size = np.max(bounds[1] - bounds[0])\n"
            "    scale_factor = (target_cm / 100.0) / current_size\n"
            "    mesh.apply_scale(scale_factor)\n"
            "    min_z = mesh.bounds[0][2]\n"
            "    mesh.apply_translation([0, 0, -min_z])\n"
            "    mesh.export(output_path)\n"
            "    return {'watertight': mesh.is_watertight, 'scale': scale_factor, 'path': output_path}\n"
        ),
    },
    {
        "instruction": "Crée un endpoint FastAPI pour l'inférence DeepSeek-R1 via Ollama",
        "input": "Accepter un prompt, retourner la réponse avec chain-of-thought séparé",
        "output": (
            "from fastapi import FastAPI\nfrom pydantic import BaseModel\nimport httpx\n\n"
            "app = FastAPI()\n\n"
            "class InferRequest(BaseModel):\n"
            "    prompt: str\n"
            "    model: str = 'deepseek-r1:7b'\n"
            "    temperature: float = 0.2\n\n"
            "@app.post('/nova/infer')\nasync def nova_infer(req: InferRequest):\n"
            "    async with httpx.AsyncClient(timeout=120) as client:\n"
            "        r = await client.post(\n"
            "            'http://localhost:11434/api/chat',\n"
            "            json={'model': req.model, 'messages': [{'role': 'user', 'content': req.prompt}],\n"
            "                  'stream': False, 'options': {'temperature': req.temperature}}\n"
            "        )\n"
            "    content = r.json()['message']['content']\n"
            "    think, answer = '', content\n"
            "    if '<think>' in content and '</think>' in content:\n"
            "        think = content.split('<think>')[1].split('</think>')[0].strip()\n"
            "        answer = content.split('</think>')[-1].strip()\n"
            "    return {'think': think, 'answer': answer, 'model': req.model}\n"
        ),
    },
]


def format_example(ex: dict) -> dict:
    return {
        "prompt": TEMPLATE.format(
            instruction=ex["instruction"],
            input=ex["input"],
            output="",
        ).rstrip(),
        "completion": ex["output"],
        "text": TEMPLATE.format(**ex),
    }


def split_and_save(examples: list[dict], train_ratio=0.8, valid_ratio=0.1):
    random.shuffle(examples)
    n = len(examples)
    t = int(n * train_ratio)
    v = int(n * valid_ratio)

    splits = {
        "train": examples[:t],
        "valid": examples[t:t + v],
        "test":  examples[t + v:],
    }
    for name, data in splits.items():
        path = os.path.join(DATASET_DIR, f"{name}.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for ex in data:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        print(f"[dataset] {name}.jsonl → {len(data)} exemples")


if __name__ == "__main__":
    formatted = [format_example(ex) for ex in SEED_EXAMPLES]
    # Augmentation simple : dupliquer pour avoir un dataset minimal
    augmented = formatted * max(1, 20 // len(formatted))
    split_and_save(augmented)
    print(f"\n[OK] Dataset prêt dans {DATASET_DIR}")
    print("Ajoute tes propres exemples dans SEED_EXAMPLES puis relance ce script.")
