# Next.js frontend for the Align urgent-care demo.
#
# BUILD CONTEXT IS THE REPO ROOT, not this directory — the app depends on the
# @align/generated-types workspace package and on the root lockfile:
#
#   docker build -f apps/urgent-care-app/Dockerfile -t align-web .
#
# The browser never calls the API directly; app/api/demo/[...path]/route.ts
# proxies server-side to ALIGN_API_BASE_URL. On Vercel that is injected by the
# `web` -> `api` service binding in vercel.json; locally it defaults to
# http://localhost:8000.

# --- deps ------------------------------------------------------------------
FROM node:20-alpine AS deps
WORKDIR /repo

# Only the manifests, so this layer caches until a dependency actually changes.
COPY package.json package-lock.json ./
COPY apps/urgent-care-app/package.json apps/urgent-care-app/
COPY packages/generated-types/package.json packages/generated-types/
RUN npm ci

# --- build -----------------------------------------------------------------
FROM node:20-alpine AS build
WORKDIR /repo
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /repo/node_modules ./node_modules
COPY package.json package-lock.json turbo.json ./
COPY packages ./packages
COPY apps/urgent-care-app ./apps/urgent-care-app

RUN npm run build --workspace=urgent-care-app

# --- runtime ---------------------------------------------------------------
FROM node:20-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

# `output: "standalone"` traces the runtime deps into .next/standalone, so there
# is no node_modules install here. With outputFileTracingRoot set to the repo
# root, the server entrypoint lands at apps/urgent-care-app/server.js and
# hoisted deps sit in a sibling node_modules — copy the tree, keeping layout.
COPY --from=build /repo/apps/urgent-care-app/.next/standalone ./
# static/ and public/ are deliberately excluded from the trace; server.js
# expects to find them next to itself.
COPY --from=build /repo/apps/urgent-care-app/.next/static ./apps/urgent-care-app/.next/static
COPY --from=build /repo/apps/urgent-care-app/public ./apps/urgent-care-app/public

# node:alpine ships an unprivileged `node` user (uid 1000).
USER node
EXPOSE 3000

CMD ["node", "apps/urgent-care-app/server.js"]
