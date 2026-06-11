#!/usr/bin/env bash

# Yandere VPN — скрипт установки и управления через Docker
# Запуск: bash <(curl -sL https://raw.githubusercontent.com/heratxd/YandereVPN/main/install.sh)
# 
# === АВТОМАТИЧЕСКИЙ ЗАПУСК (БЕЗ ДИАЛОГОВ) ===
#
# 1. Запуск прямо с GitHub (для чистой установки или если папки ещё нет):
# bash <(curl -sL https://raw.githubusercontent.com/heratxd/YandereVPN/main/install.sh) install <BOT_TOKEN> <ADMIN_ID>
# bash <(curl -sL https://raw.githubusercontent.com/heratxd/YandereVPN/main/install.sh) update [COMMIT_OR_BRANCH]
# bash <(curl -sL https://raw.githubusercontent.com/heratxd/YandereVPN/main/install.sh) reset [COMMIT_OR_BRANCH]
#
# 2. Локальный запуск:
# bash install.sh update [COMMIT_OR_BRANCH]
# bash install.sh reset [COMMIT_OR_BRANCH]

set -e

INSTALL_DIR="/root/YandereVPN"
REPO_URL="https://github.com/heratxd/YandereVPN.git"
SERVICE_NAME="yandere-vpn-bot"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33'
CYAN='\033[0;36m'
NC='\033[0m'

print_header() {
    echo -e "\n${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}\n"
}

print_ok() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_err() {
    echo -e "${RED}[✗]${NC} $1"
}

# Поиск и отключение старого бот-сервиса (если переходим с systemd)
cleanup_old_bot_install() {
    print_header "Поиск и отключение старых systemd-служб"

    local found_services=()
    for svc in "yadreno-vpn" "yadreno" "yandere-vpn" "vpn-bot" "tg-vpn-bot" "vpn_bot"; do
        if [ -f "/etc/systemd/system/${svc}.service" ]; then
            found_services+=("${svc}.service")
        fi
    done

    # Ищем по содержимому файлов служб
    for svc_file in /etc/systemd/system/*.service; do
        if [ -f "$svc_file" ]; then
            local fname=$(basename "$svc_file")
            if [[ ! " ${found_services[@]} " =~ " ${fname} " ]]; then
                if grep -E -q "ExecStart=.*(python|venv).*/main\.py" "$svc_file" || grep -q -E "yadreno|yandere" "$svc_file"; then
                    found_services+=("$fname")
                fi
            fi
        fi
    done

    if [ ${#found_services[@]} -gt 0 ]; then
        print_warn "Обнаружены старые службы бота: ${found_services[*]}"
        for old_svc in "${found_services[@]}"; do
            print_warn "Остановка и удаление службы: $old_svc"
            
            # Резервное копирование конфига и БД перед удалением
            local old_dir=""
            old_dir=$(grep -oP "WorkingDirectory=\K.*" "/etc/systemd/system/$old_svc" 2>/dev/null | tr -d '\r' || true)
            if [ -n "$old_dir" ] && [ -d "$old_dir" ]; then
                if [ -f "$old_dir/config.py" ]; then
                    cp "$old_dir/config.py" /tmp/yandere_old_config.py
                    print_ok "Старый config.py сохранен в /tmp/yandere_old_config.py"
                fi
                if [ -f "$old_dir/database/vpn_bot.db" ]; then
                    cp "$old_dir/database/vpn_bot.db" /tmp/yandere_old_db.db
                    print_ok "База данных SQLite сохранена"
                elif [ -f "$old_dir/vpn_bot.db" ]; then
                    cp "$old_dir/vpn_bot.db" /tmp/yandere_old_db.db
                    print_ok "База данных SQLite сохранена"
                fi
            fi

            systemctl stop "$old_svc" 2>/dev/null || true
            systemctl disable "$old_svc" 2>/dev/null || true
            rm -f "/etc/systemd/system/$old_svc"
            print_ok "Служба $old_svc удалена"
        done
        systemctl daemon-reload
    else
        print_ok "Старых systemd-служб бота не найдено"
    fi

    # Завершаем старые процессы python если остались
    local pids=$(pgrep -f "python.*main\.py" || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            local cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || true)
            if [[ ! "$cmdline" =~ "/tmp/" ]]; then
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
    fi
}

# Функция слияния настроек config.py
merge_old_config() {
    local source_config=""
    if [ -f "/tmp/yandere_old_config.py" ]; then
        source_config="/tmp/yandere_old_config.py"
    elif [ -f "/tmp/yandere_config_backup.py" ]; then
        source_config="/tmp/yandere_config_backup.py"
    fi

    if [ -n "$source_config" ] && [ -f "$INSTALL_DIR/config.py" ]; then
        print_header "Миграция старых настроек в новый config.py"
        
        cat << 'EOF' > /tmp/migrate_config.py
import runpy
import sys
import ast

old_path = sys.argv[1]
new_path = sys.argv[2]

try:
    old_vars = runpy.run_path(old_path)
except Exception as e:
    print(f"Ошибка чтения старого конфига: {e}")
    sys.exit(1)

try:
    with open(new_path, 'r', encoding='utf-8') as f:
        content = f.read()
    lines = content.splitlines(keepends=True)
except Exception as e:
    print(f"Ошибка чтения шаблона конфига: {e}")
    sys.exit(1)

keys_to_migrate = {
    k: v for k, v in old_vars.items()
    if k.isupper() and not k.startswith('__') and not isinstance(v, (type, type(sys)))
}

try:
    tree = ast.parse(content)
except Exception as e:
    print(f"Ошибка парсинга шаблона конфига: {e}")
    sys.exit(1)

replacements = []
replaced_keys = set()

for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if var_name in keys_to_migrate:
                    val = keys_to_migrate[var_name]
                    # Избегаем изменения URL репозитория на старый, если изменилось имя
                    if var_name == "GITHUB_REPO_URL" and "Yadreno" in val:
                        val = "https://github.com/heratxd/YandereVPN.git"
                    
                    if isinstance(val, str):
                        formatted_val = f'"{val}"'
                    else:
                        formatted_val = repr(val)
                    new_text = f"{var_name} = {formatted_val}"
                    replacements.append((node.lineno, node.end_lineno, new_text))
                    replaced_keys.add(var_name)

replacements.sort(key=lambda x: x[0], reverse=True)
for start, end, new_text in replacements:
    lines[start-1:end] = [new_text + '\n']

remaining_keys = set(keys_to_migrate.keys()) - replaced_keys
if remaining_keys:
    lines.append("\n# === Дополнительные настройки из старого конфига ===\n")
    for key in sorted(remaining_keys):
        val = keys_to_migrate[key]
        if isinstance(val, str):
            formatted_val = f'"{val}"'
        else:
            formatted_val = repr(val)
        lines.append(f"{key} = {formatted_val}\n")

try:
    with open(new_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print("✅ Настройки из старого config.py успешно импортированы!")
except Exception as e:
    print(f"Ошибка записи нового конфига: {e}")
    sys.exit(1)
EOF

        python3 /tmp/migrate_config.py "$source_config" "$INSTALL_DIR/config.py"
        rm -f /tmp/migrate_config.py
        rm -f /tmp/yandere_old_config.py
        rm -f /tmp/yandere_config_backup.py
    fi
}

# Запрос настроек у пользователя
ask_config() {
    print_header "Настройка конфигурации"

    if [ "$AUTO_MODE" = "1" ]; then
        NEED_WRITE_CONFIG=1
        print_ok "Автоматический режим установки"
        return 0
    fi

    if [ -f "$INSTALL_DIR/config.py" ]; then
        echo -e "${YELLOW}Обнаружен существующий config.py${NC}"
        read -p "Использовать существующие настройки? (Y/n): " use_existing
        use_existing=${use_existing:-Y}
        if [[ "$use_existing" =~ ^[YyДд]$ ]]; then
            print_ok "Используем существующий config.py"
            return 0
        fi
    fi

    echo ""
    echo -e "${CYAN}Введите данные для настройки бота:${NC}"
    echo ""

    while true; do
        read -p "BOT_TOKEN (от @BotFather): " bot_token
        if [ -n "$bot_token" ]; then
            break
        fi
        print_err "BOT_TOKEN не может быть пустым!"
    done

    while true; do
        read -p "ADMIN_IDS (ваш Telegram ID через запятую): " admin_id
        if [ -n "$admin_id" ]; then
            break
        fi
        print_err "ADMIN_IDS не может быть пустым!"
    done

    BOT_TOKEN="$bot_token"
    # Превращаем строку ID через запятую в массив для config.py
    ADMIN_ID=$(echo "$admin_id" | sed 's/ //g')
    NEED_WRITE_CONFIG=1
    print_ok "Данные получены"
}

# Запись config.py
write_config() {
    if [ "$NEED_WRITE_CONFIG" != "1" ]; then
        return 0
    fi

    cp "$INSTALL_DIR/config.py.example" "$INSTALL_DIR/config.py"

    sed -i "s|\"ВАШ_ТОКЕН_БОТА\"|\"$BOT_TOKEN\"|g" "$INSTALL_DIR/config.py"
    sed -i "s|12345678|$ADMIN_ID|g" "$INSTALL_DIR/config.py"

    print_ok "config.py успешно создан"
}

# Проверка и установка Docker & Docker Compose
install_docker() {
    print_header "Проверка и установка Docker"

    if ! command -v docker &> /dev/null; then
        print_warn "Docker не найден. Устанавливаем официальный Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh
        systemctl start docker || true
        systemctl enable docker || true
        print_ok "Docker успешно установлен!"
    else
        print_ok "Docker уже установлен"
    fi

    # Проверяем docker compose (v2) или docker-compose (v1)
    if ! docker compose version &> /dev/null; then
        if command -v docker-compose &> /dev/null; then
            print_ok "Docker Compose (v1) доступен"
        else
            print_warn "Docker Compose не найден. Установка плагина docker-compose-plugin..."
            apt-get update -qq && apt-get install -y -qq docker-compose-plugin > /dev/null 2>&1 || true
            if ! docker compose version &> /dev/null; then
                print_err "Не удалось автоматически установить Docker Compose. Пожалуйста, установите его вручную."
                exit 1
            fi
            print_ok "Docker Compose успешно установлен!"
        fi
    else
        print_ok "Docker Compose (v2) доступен"
    fi
}

# Запуск Compose
run_docker_compose() {
    print_header "Запуск Docker контейнеров"
    cd "$INSTALL_DIR"

    # Определяем команду compose
    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null && command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    fi

    $compose_cmd down --remove-orphans || true
    $compose_cmd up --build -d
    print_ok "Контейнеры запущены успешно!"
}

# ============================================================
# ПУНКТ 1: УСТАНОВКА
# ============================================================
do_install() {
    print_header "🚀 Установка Yandere VPN"

    cleanup_old_bot_install
    install_docker

    if [ -d "$INSTALL_DIR" ] && [ -d "$INSTALL_DIR/.git" ]; then
        print_warn "Yandere VPN уже установлен в $INSTALL_DIR"
        if [ "$AUTO_MODE" = "1" ]; then
            reinstall_choice="1"
        else
            echo ""
            echo "  1) Переустановить (удалить текущую папку и установить заново)"
            echo "  2) Отмена"
            read -p "Выберите [1-2]: " reinstall_choice
        fi
        if [ "$reinstall_choice" != "1" ]; then
            echo "Установка отменена."
            return 0
        fi

        # Останавливаем старые докер контейнеры
        if [ -f "$INSTALL_DIR/docker-compose.yml" ]; then
            cd "$INSTALL_DIR"
            docker compose down || docker-compose down || true
        fi

        # Сохраняем конфиг и БД перед очисткой каталога
        if [ -f "$INSTALL_DIR/config.py" ]; then
            cp "$INSTALL_DIR/config.py" /tmp/yandere_config_backup.py
            BACKUP_CONFIG=1
        fi
        if [ -f "$INSTALL_DIR/database/vpn_bot.db" ]; then
            cp "$INSTALL_DIR/database/vpn_bot.db" /tmp/yandere_db_backup.db
            BACKUP_DB=1
        elif [ -f "$INSTALL_DIR/vpn_bot.db" ]; then
            cp "$INSTALL_DIR/vpn_bot.db" /tmp/yandere_db_backup.db
            BACKUP_DB=1
        fi
        rm -rf "$INSTALL_DIR"
    fi

    ask_config

    print_header "Загрузка кода Yandere VPN"
    git clone "$REPO_URL" "$INSTALL_DIR" -q
    cd "$INSTALL_DIR"
    print_ok "Репозиторий клонирован в $INSTALL_DIR"

    # Восстановление резервных копий
    if [ "$BACKUP_CONFIG" = "1" ] && [ -f "/tmp/yandere_config_backup.py" ]; then
        cp /tmp/yandere_config_backup.py "$INSTALL_DIR/config.py"
        rm /tmp/yandere_config_backup.py
        print_ok "Конфигурация восстановлена"
        NEED_WRITE_CONFIG=0
    fi
    
    mkdir -p "$INSTALL_DIR/database"
    mkdir -p "$INSTALL_DIR/logs"

    if [ "$BACKUP_DB" = "1" ] && [ -f "/tmp/yandere_db_backup.db" ]; then
        cp /tmp/yandere_db_backup.db "$INSTALL_DIR/database/vpn_bot.db"
        rm /tmp/yandere_db_backup.db
        print_ok "База данных SQLite восстановлена"
    fi

    if [ -f "/tmp/yandere_old_db.db" ]; then
        cp /tmp/yandere_old_db.db "$INSTALL_DIR/database/vpn_bot.db"
        rm -f "/tmp/yandere_old_db.db"
        print_ok "База данных старого бота успешно импортирована"
    fi

    write_config
    merge_old_config

    # Проверка на наличие 3x-ui на хосте
    if [ ! -d "/etc/x-ui" ] && [ ! -f "/usr/local/x-ui/bin/x-ui.db" ]; then
        print_warn "Локальная панель 3x-ui не обнаружена на сервере."
        if [ "$AUTO_MODE" != "1" ]; then
            read -p "Хотите автоматически установить официальную панель 3x-ui на хост? (y/N): " install_xui
            install_xui=${install_xui:-N}
            if [[ "$install_xui" =~ ^[YyДд]$ ]]; then
                print_header "Установка 3x-ui..."
                bash <(curl -Ls https://raw.githubusercontent.com/mhsanaei/3x-ui/master/install.sh)
                print_ok "3x-ui успешно установлена!"
            fi
        fi
    fi

    # Запускаем СУБД PostgreSQL
    print_header "Инициализация базы данных PostgreSQL"
    local compose_cmd="docker compose"
    if ! docker compose version &> /dev/null && command -v docker-compose &> /dev/null; then
        compose_cmd="docker-compose"
    fi
    $compose_cmd up -d db
    print_ok "Контейнер базы данных запущен, ожидаем инициализации..."
    sleep 4

    # Запускаем автоопределение 3x-ui внутри Docker-контейнера в интерактивном режиме
    print_header "Настройка привязки 3x-ui"
    $compose_cmd run --rm yandere-vpn-bot python3 detect_xui.py || true

    run_docker_compose

    print_header "✅ Установка завершена!"
    echo -e "  Директория проекта: ${GREEN}$INSTALL_DIR${NC}"
    echo -e "  Логи: ${CYAN}docker logs -f yandere-vpn-bot${NC}"
    echo -e "  Перезапуск: ${CYAN}docker restart yandere-vpn-bot${NC}"
}

# ============================================================
# ПУНКТ 2: ОБНОВЛЕНИЕ (git pull)
# ============================================================
do_soft_update() {
    print_header "🔄 Обновление бота"

    if [ ! -d "$INSTALL_DIR/.git" ]; then
        print_err "Yandere VPN не установлен в $INSTALL_DIR"
        return 1
    fi

    cd "$INSTALL_DIR"

    # Сохраняем локальные правки в stash если есть
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        print_warn "Сохраняем локальные изменения во временный stash..."
        git stash -q
        STASHED=1
    fi

    if [ -n "$TARGET_COMMIT" ]; then
        git fetch -q origin
        git checkout -q "$TARGET_COMMIT"
    else
        git checkout -q main
        git pull -q origin main
    fi

    if [ "$STASHED" = "1" ]; then
        git stash pop -q 2>/dev/null || print_warn "Локальные правки не удалось применить автоматически"
    fi

    print_ok "Код обновлен"

    run_docker_compose
}

# ============================================================
# ПУНКТ 3: СБРОС И ПЕРЕЗАПИСЬ (git reset --hard)
# ============================================================
do_hard_reset() {
    print_header "⚠️ Сброс изменений и перезапись"

    if [ ! -d "$INSTALL_DIR/.git" ]; then
        print_err "Yandere VPN не установлен в $INSTALL_DIR"
        return 1
    fi

    echo -e "${RED}Внимание! Все ваши ручные изменения в коде будут стерты.${NC}"
    echo -e "${YELLOW}Файлы config.py и база данных затронуты НЕ будут.${NC}"
    if [ "$AUTO_MODE" = "1" ]; then
        confirm="y"
    else
        read -p "Вы уверены, что хотите сбросить код? (y/N): " confirm
    fi
    if [[ ! "$confirm" =~ ^[YyДд]$ ]]; then
        echo "Отменено."
        return 0
    fi

    cd "$INSTALL_DIR"

    git fetch origin -q
    local target="origin/main"
    if [ -n "$TARGET_COMMIT" ]; then
        target="$TARGET_COMMIT"
    fi

    git reset --hard "$target" -q
    git clean -fd -q
    print_ok "Код полностью перезаписан до версии $target"

    run_docker_compose
}

# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================
show_menu() {
    clear
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════╗"
    echo "  ║       🌐 Yandere VPN Manager          ║"
    echo "  ╚═══════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  1) 🚀 Установить / Переустановить бота"
    echo "  2) 🔄 Обновить бот до свежей версии (git pull)"
    echo "  3) ⚠️  Сбросить код бота (сброс ручных изменений)"
    echo ""
    echo "  0) Выход"
    echo ""
    read -p "  Выберите действие [0-3]: " choice

    case $choice in
        1) do_install ;;
        2) do_soft_update ;;
        3) do_hard_reset ;;
        0) echo "Пока! 👋"; exit 0 ;;
        *) echo "Неверный выбор"; return 1 ;;
    esac
}

# Проверка root-прав
if [ "$EUID" -ne 0 ]; then
    print_err "Скрипт должен быть запущен от имени администратора (root/sudo)"
    exit 1
fi

# Проверка авто-режима
if [ -n "$1" ]; then
    ACTION="$1"
    export AUTO_MODE="1"
    
    case "$ACTION" in
        install)
            if [ -z "$2" ] || [ -z "$3" ]; then
                print_err "Недостаточно параметров для автоустановки."
                echo "Использование: bash install.sh install <BOT_TOKEN> <ADMIN_ID>"
                exit 1
            fi
            export BOT_TOKEN="$2"
            export ADMIN_ID="$3"
            do_install 
            ;;
        update)
            export TARGET_COMMIT="$2"
            do_soft_update 
            ;;
        reset)
            export TARGET_COMMIT="$2"
            do_hard_reset 
            ;;
        *)
            print_err "Неизвестная команда: $ACTION"
            exit 1
            ;;
    esac
    exit 0
fi

show_menu
