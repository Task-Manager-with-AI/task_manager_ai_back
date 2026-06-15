FROM python:3.12-slim
WORKDIR /app

ARG TRANSCRIPTION_PROVIDER=openai
ARG LOCAL_WHISPER_MODEL=tiny
ENV HF_HOME=/app/.cache/huggingface \
    TRANSCRIPTION_PROVIDER=${TRANSCRIPTION_PROVIDER} \
    LOCAL_WHISPER_MODEL=${LOCAL_WHISPER_MODEL}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Pre-cache local Whisper weights only when building for TRANSCRIPTION_PROVIDER=local
RUN if [ "$TRANSCRIPTION_PROVIDER" = "local" ]; then \
      python -c "from faster_whisper import WhisperModel; WhisperModel('${LOCAL_WHISPER_MODEL}', device='cpu', compute_type='int8'); print('Whisper weights cached:', '${LOCAL_WHISPER_MODEL}')"; \
    else \
      echo "Skipping Whisper weight cache (TRANSCRIPTION_PROVIDER=${TRANSCRIPTION_PROVIDER})"; \
    fi

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
