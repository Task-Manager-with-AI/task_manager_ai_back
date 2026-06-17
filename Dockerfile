FROM python:3.12-slim
WORKDIR /app

# Render uses groq — installs requirements-render.txt (no faster-whisper).
# For local Whisper in Docker: docker build --build-arg TRANSCRIPTION_PROVIDER=local .
ARG TRANSCRIPTION_PROVIDER=groq
ARG LOCAL_WHISPER_MODEL=tiny
ARG EMBEDDING_PROVIDER=local
ARG LOCAL_EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
ENV HF_HOME=/app/.cache/huggingface \
    TRANSCRIPTION_PROVIDER=${TRANSCRIPTION_PROVIDER} \
    LOCAL_WHISPER_MODEL=${LOCAL_WHISPER_MODEL} \
    EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER} \
    LOCAL_EMBEDDING_MODEL=${LOCAL_EMBEDDING_MODEL}

# ffprobe still used to measure audio duration when transcribing via Groq/OpenAI APIs
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-render.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && if [ "$TRANSCRIPTION_PROVIDER" = "local" ]; then \
         pip install --no-cache-dir -r requirements.txt; \
       else \
         pip install --no-cache-dir -r requirements-render.txt; \
       fi

# Pre-cache local Whisper weights only when building for TRANSCRIPTION_PROVIDER=local
RUN if [ "$TRANSCRIPTION_PROVIDER" = "local" ]; then \
      python -c "from faster_whisper import WhisperModel; WhisperModel('${LOCAL_WHISPER_MODEL}', device='cpu', compute_type='int8'); print('Whisper weights cached:', '${LOCAL_WHISPER_MODEL}')"; \
    else \
      echo "Skipping Whisper weight cache (TRANSCRIPTION_PROVIDER=${TRANSCRIPTION_PROVIDER})"; \
    fi

# Pre-cache local embedding model for RAG (avoids HuggingFace download at runtime on Render)
RUN if [ "$EMBEDDING_PROVIDER" = "local" ]; then \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${LOCAL_EMBEDDING_MODEL}'); print('Embedding model cached:', '${LOCAL_EMBEDDING_MODEL}')"; \
    else \
      echo "Skipping embedding model cache (EMBEDDING_PROVIDER=${EMBEDDING_PROVIDER})"; \
    fi

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
