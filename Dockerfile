FROM python:3.12-slim
WORKDIR /app

ARG LOCAL_WHISPER_MODEL=tiny
ENV HF_HOME=/app/.cache/huggingface \
    LOCAL_WHISPER_MODEL=${LOCAL_WHISPER_MODEL}

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -c "from faster_whisper import WhisperModel; print('faster-whisper OK')" \
    && python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['LOCAL_WHISPER_MODEL'], device='cpu', compute_type='int8'); print('Whisper weights cached:', os.environ['LOCAL_WHISPER_MODEL'])"

COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
