FROM python:3.11-slim

RUN pip install --no-cache-dir fastapi uvicorn pyjwt httpx requests aiohttp

WORKDIR /app

COPY server.py /app/
COPY .env.example /app/.env.example

EXPOSE 9090

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9090"]
