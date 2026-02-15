#!/bin/zsh

# Caminho relativo para a pasta do projeto (onde o script está)
# Garante que PROJECT_DIR seja o caminho absoluto REAL do diretório onde este arquivo (ou link) aponta
PROJECT_DIR="${0:A:h}"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"

echo "🚀 Iniciando Fluxo Barzar Print..."

# Função para abrir comando em novo terminal (macOS AppleScript)
# Nota: Usamos aspas simples e duplas escapadas para lidar com espaços no caminho
run_in_new_terminal() {
    local title=$1
    local cmd=$2
    osascript -e "tell application \"Terminal\"
        do script \"cd '$PROJECT_DIR' && echo -n -e '\\\\033]0;$title\\\\007' && $cmd\"
    end tell"
}

# 1. Iniciar Servidor Flask
echo " - Iniciando Servidor (Porta 5001)..."
run_in_new_terminal "Barzar: Server" "'$VENV_PYTHON' server.py"

# 2. Iniciar Cloudflare Tunnel
echo " - Iniciando Tunnel (api.exemplo.com)..."
run_in_new_terminal "Barzar: Tunnel" "cloudflared tunnel run --url http://127.0.0.1:5001 barzar"

# 3. Iniciar Monitor da Impressora
echo " - Iniciando Monitor Impressora (Bluetooth)..."
run_in_new_terminal "Barzar: Printer" "'$VENV_PYTHON' print_phomemo.py"

# 4. Iniciar Bridge (Ponte)
echo " - Iniciando Bridge Local..."
run_in_new_terminal "Barzar: Bridge" "'$VENV_PYTHON' bridge.py"

echo "✅ Todos os componentes foram abertos em novas janelas do Terminal."
