FROM node:22-alpine

RUN corepack enable

ENV NEXT_TELEMETRY_DISABLED=1

WORKDIR /code

COPY package.json pnpm-workspace.yaml pnpm-lock.yaml .npmrc ./
COPY web/package.json ./web/package.json

COPY packages/api-client/package.json ./packages/api-client/package.json

RUN pnpm install --frozen-lockfile

COPY tsconfig.base.json ./
COPY web ./web
COPY packages ./packages

EXPOSE 3000

CMD ["pnpm", "dev"]
