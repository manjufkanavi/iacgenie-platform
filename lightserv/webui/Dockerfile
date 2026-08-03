# Build stage
FROM node:22-slim AS builder

WORKDIR /app
COPY package*.json ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

# Production stage
FROM node:22-slim AS runner

WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3070

# Copy standalone output
ARG NEXT_PUBLIC_API_URL=http://lightserp-api:3071
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# Update package.json for standalone
RUN node -e "const pkg=require('./package.json'); delete pkg.devDependencies; pkg.scripts={}; require('fs').writeFileSync('package.json', JSON.stringify(pkg,null,2))"

EXPOSE 3070

CMD ["node", "server.js"]
