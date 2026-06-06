---
name: dockerfile-gen
description: Generate a production-ready Dockerfile (and .dockerignore) for the project. Use to containerize an app or /dockerfile-gen.
---

Write a Dockerfile for this project.

1. Detect the runtime, version, package manager, build step, and start command from the project files (don't guess the start command — find it in package.json scripts, a Procfile, the main module, etc.).
2. Write a **multi-stage** Dockerfile where it helps (build stage + slim runtime stage) to keep the image small.
3. Apply best practices: pin a specific base image tag, copy lockfiles and install deps before copying source (layer caching), run as a non-root user, set a sensible `WORKDIR`, expose the right port, and use the real start command.
4. Also produce a `.dockerignore` (node_modules, .git, .env, build artifacts) so the build context stays small.
5. Note any assumptions (port, env vars needed) the user should verify. Output both files.
