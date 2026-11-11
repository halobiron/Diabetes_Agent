FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
# The deploy target (App Runner) has no GPU, so install the CPU build of torch first; the
# default CUDA build adds several GB of NVIDIA libraries the container cannot use.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Bake the ~2.3 GB embedding model into the image so a cold start does not download it.
ENV HF_HOME=/opt/hf
# Loads exactly as the app does (tools/semantic_embeddings.py). Only that file is copied
# first, so editing other code does not invalidate the cached model layer.
# bge-m3's main revision ships pytorch_model.bin, and transformers also fetches a converted
# model.safetensors from a PR revision (another 2.3 GB). Offline, the .bin alone loads, so
# every cached revision other than main is deleted.
COPY tools/__init__.py tools/semantic_embeddings.py /app/tools/
RUN python -c "from tools.semantic_embeddings import SemanticEmbeddingModel as M; M().embed_texts(['ok'])" \
    && python -c "from huggingface_hub import scan_cache_dir as s; c = s(); c.delete_revisions(*[r.commit_hash for repo in c.repos for r in repo.revisions if 'main' not in r.refs]).execute()"
# The model is in the image; never call Hugging Face at runtime.
ENV HF_HUB_OFFLINE=1

COPY . /app

EXPOSE 8000
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
