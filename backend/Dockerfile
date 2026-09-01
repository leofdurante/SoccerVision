# Optional containerized run — see README "Running locally" for the
# faster, recommended path (plain venv + npm run dev). This exists
# because docker-compose.yml is part of the expected repo layout, not
# because the project needs cloud infrastructure to run.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
