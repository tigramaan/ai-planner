FROM python:3.13-slim
WORKDIR /worker
RUN addgroup --system planner && adduser --system --ingroup planner planner
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2,<27" \
    && python -m pip install --no-cache-dir -r requirements.txt
COPY worker.py .
USER planner
CMD ["python", "worker.py"]
