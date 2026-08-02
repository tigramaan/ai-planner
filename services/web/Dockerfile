FROM node:24-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install --omit=optional
COPY . .
RUN npm run build
FROM node:24-alpine
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S planner && adduser -S planner -G planner
COPY --from=build --chown=planner:planner /app/.next/standalone ./
COPY --from=build --chown=planner:planner /app/.next/static ./.next/static
COPY --from=build --chown=planner:planner /app/public ./public
USER planner
EXPOSE 3000
CMD ["node", "server.js"]
