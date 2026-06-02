"""NEXUS9 shared services.

Provider-agnostic building blocks shared by routers AND background jobs
(auto_factory). Lives here — not inside any router — so nothing imports a
router to reuse it (CLAUDE.md guardrail: no router-to-router imports).

Image generation:
  • comfyui_images — FLUX Schnell via ComfyUI (local, free)
  • openai_images  — OpenAI gpt-image-1 (cloud, paid)
  • image_factory  — single dispatch point (comfyui | gpt-image-1 | auto)
"""
