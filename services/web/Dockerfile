FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY services/web/package.json ./services/web/package.json
RUN npm ci
COPY services/web ./services/web
RUN npm run web:build
FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S planner && adduser -S planner -G planner
COPY --from=build --chown=planner:planner /app/services/web/.next/standalone ./
COPY --from=build --chown=planner:planner /app/services/web/.next/static ./services/web/.next/static
COPY --from=build --chown=planner:planner /app/services/web/public ./services/web/public
USER planner
EXPOSE 3000
CMD ["node", "services/web/server.js"]
