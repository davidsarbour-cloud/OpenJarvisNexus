# ── Stage 1 : Build ──────────────────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./

# react 19 vs @arwes/react (peer react@18) : on tolere les peer deps.
# npm config set ecrit dans .npmrc => deterministe (plus fiable qu'ENV).
# npm ci en premier (rapide), fallback npm install si peer deps cassent.
RUN npm config set legacy-peer-deps true \
 && (npm ci --prefer-offline \
     || (echo "npm ci a echoue, fallback npm install..." && npm install --no-audit --no-fund))

COPY . .

# On override l'outDir pour ne pas écrire dans ../src/openjarvis/...
RUN npx vite build --outDir /app/dist --emptyOutDir

# ── Stage 2 : Serve (nginx) ───────────────────────────────
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
