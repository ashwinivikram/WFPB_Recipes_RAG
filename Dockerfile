FROM python:3.11-slim

WORKDIR /app

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies into a virtual environment
RUN uv sync --no-dev

# Ensure the virtual environment is used
ENV PATH="/app/.venv/bin:$PATH"

# Download the BM25 model at build time to avoid downloading on startup
RUN python -c "from fastembed import SparseTextEmbedding; SparseTextEmbedding('Qdrant/bm25')"

# Copy the rest of the application
COPY . .

# Run the application (shell form to expand PORT)
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
