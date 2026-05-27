# Agent avatar images

Drop a PNG/JPG/WebP per agent here, named after the agent ID (lowercase,
same as what `/v1/agents` returns):

```
public/agents/
├── jarvis.png
├── ultron.png
├── qwen.png
├── cortana.png
├── bruce.png
├── nova.png
└── forge.png
```

Format guidelines:
- 512×512 px is plenty (rendered at 120 px in the agent detail panel).
- Square / round source helps — the avatar disc clips with `border-radius: 50%`.
- PNG with transparent background sits well over the radial-gradient
  backdrop and the accent border; JPG works but loses the glow halo.
- Keep file size under ~200 KB; these load on every panel open.

Behavior:
- If the file exists, it shows up immediately in the slide-in panel
  on `/agent-network` (click any node).
- If the file is missing, `onError` flips to the Lucide icon fallback
  (Cpu/Brain/Atom/…). No build step required — drop and refresh.
