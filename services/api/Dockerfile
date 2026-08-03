FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system planner && adduser --system --ingroup planner planner
COPY pyproject.toml ./
RUN python -m pip install --no-cache-dir --upgrade "pip>=26.1.2,<27" \
    && python -m pip install --no-cache-dir .
COPY . .
USER planner
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
