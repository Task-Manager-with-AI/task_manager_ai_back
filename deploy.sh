#!/bin/bash
set -e

# ── Deploy script for task_manager_ai_back on Ubuntu VM ──────────────────────
# Run this once from inside the task_manager_ai_back/ directory on the VM.

echo "==> Verificando Docker..."
if ! command -v docker &> /dev/null; then
  echo "Docker no encontrado. Instalando..."
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  echo ""
  echo "IMPORTANTE: Docker instalado. Debes cerrar sesión y volver a conectarte"
  echo "para que los permisos de grupo surtan efecto. Luego ejecuta este script de nuevo."
  exit 0
fi

echo "==> Verificando .env..."
if [ ! -f .env ]; then
  echo "Creando .env desde .env.example..."
  cp .env.example .env
  echo ""
  echo "IMPORTANTE: Edita .env y agrega tu DEEPSEEK_API_KEY antes de continuar."
  echo "  nano .env"
  echo ""
  read -r -p "Presiona Enter cuando hayas guardado la clave API en .env..."
fi

echo "==> Construyendo imagen Docker (esto puede tardar 5-15 minutos la primera vez)..."
docker compose build

echo "==> Iniciando servicio..."
docker compose up -d

echo ""
echo "==> Estado del contenedor:"
docker compose ps

echo ""
echo "==> Logs recientes (Ctrl+C para salir):"
docker compose logs --tail=30 -f
