# ── Stage 1 : Build ──────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .

# On override l'outDir pour ne pas écrire dans ../src/openjarvis/...
RUN npx vite build --outDir /app/dist --emptyOutDir

# ── Stage 2 : Serve (nginx) ───────────────────────────────
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
