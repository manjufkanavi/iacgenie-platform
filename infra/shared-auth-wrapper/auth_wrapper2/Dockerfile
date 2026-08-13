FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production 2>/dev/null || npm install --production
COPY app.js .
EXPOSE 9090
ENV PORT=9090
CMD ["node", "app.js"]
