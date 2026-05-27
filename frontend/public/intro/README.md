# Nexus9 boot intro video

Drop one file here named **`boot.mp4`** (or `.webm` as a secondary
fallback) and the splash overlay will play it instead of the styled
HUD placeholder.

```
public/intro/
└── boot.mp4         ← your file
```

## When it plays

The intro plays **once per server boot**:

- Backend exposes `GET /v1/boot/info` → `{ boot_id, started_at }`.
  `boot_id` is a fresh uuid generated at every uvicorn process start.
- Frontend reads the boot_id on first paint and compares it with what
  it stored in `localStorage('nexus9.intro.boot-id')`. Different = new
  server boot → play. Same = page refresh / SPA navigation → skip.
- After the video ends (or the user clicks SKIP / hits Esc), the new
  boot_id is persisted so it won't replay until you restart uvicorn.

To force a replay without restarting the backend, clear the localStorage
key from the browser devtools console:

```js
localStorage.removeItem('nexus9.intro.boot-id')
```

## Format guidelines

- **Container**: mp4 with H.264 video + AAC audio is the most
  portable (webm/VP9 works too).
- **Resolution**: 1920×1080 is fine; the overlay scales with
  `objectFit: cover` to fill the viewport.
- **Duration**: 3–8 s. The whole purpose is to feel like a boot
  sequence, not block the user. Beyond 8 s the SKIP hint kicks in
  more visibly.
- **Audio**: muted by default (`autoPlay muted playsInline` —
  required for autoplay in modern browsers). If you want sound,
  the user has to unmute it manually; consider adding the audio
  cue to a sound file the JarvisChatPage plays instead.
- **File size**: ideally under 8 MB. Anything bigger noticeably
  delays first paint because the splash blocks the HUD.
- **Background**: dark — the HUD is black/violet, so a video that
  fades from black to your logo blends in. A bright video produces
  a harsh flash at the cut.

## How the placeholder works

While `boot.mp4` is missing, `NexusBootIntro.tsx` renders a self-
contained HUD-style sequence (animated NEXUS9 wordmark, scan lines,
fake terminal trace, progress bar to 100 %, fade out). No external
asset needed — it ships in the bundle.

The component tries to `<video src="/intro/boot.mp4">` first; on
error (404 because you haven't dropped the file yet) it falls back
to the placeholder automatically. Drop the video any time — no code
change required.
