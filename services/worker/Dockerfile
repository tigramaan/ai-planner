FROM python:3.13-slim
WORKDIR /worker
RUN addgroup --system planner && adduser --system --ingroup planner planner \
    && apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2,<27" \
    && python -m pip install --no-cache-dir -r requirements.txt
COPY worker.py entrypoint.sh ./
RUN chmod 0555 /worker/entrypoint.sh
ENTRYPOINT ["/worker/entrypoint.sh"]
