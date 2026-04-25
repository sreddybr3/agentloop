FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Upgrade pip and setuptools so the setuptools.backends._legacy build backend is available
RUN pip install --no-cache-dir --upgrade pip setuptools

# Install Python dependencies from pyproject.toml
COPY pyproject.toml .
COPY README.md .
COPY document_extractor/__init__.py document_extractor/__init__.py
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir fastapi "uvicorn[standard]"

# Copy full project
COPY . .

# Default env vars — pass GOOGLE_API_KEY at runtime: docker run -e GOOGLE_API_KEY=xxx
ENV GOOGLE_GENAI_USE_VERTEXAI=1
ENV MODEL_NAME=gemini-3.1-flash-lite-preview
ENV EXTRACTION_MODEL=gemini-3.1-flash-lite-preview
ENV LOG_LEVEL=INFO

EXPOSE 8000 8001

# Start script: ADK Web UI on 8000 + FastAPI REST on 8001
COPY <<EOF /app/start.sh
#!/bin/bash
# Start ADK Web UI on port 8000
adk web --host 0.0.0.0 --port 8000 . &

# Start FastAPI extraction API on port 8001
uvicorn document_extractor.api:app --host 0.0.0.0 --port 8001

EOF
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
