#!/bin/bash

# Yadreno VPN — скрипт установки и управления
# Запуск: bash <(curl -sL https://raw.githubusercontent.com/heratxd/YadrenoVPN/main/install.sh)
# 
# === АВТОМАТИЧЕСКИЙ ЗАПУСК (БЕЗ ДИАЛОГОВ) ===
#
# 1. Запуск прямо с GitHub (для чистой установки или если папки ещё нет):
# bash <(curl -sL https://raw.githubusercontent.com/heratxd/YadrenoVPN/main/install.sh) install <BOT_TOKEN> <ADMIN_ID>
# bash <(curl -sL https://raw.githubusercontent.com/heratxd/YadrenoVPN/main/install.sh) update [COMMIT_OR_BRANCH]
# bash <(curl -sL https://raw.githubusercontent.com/heratxd/YadrenoVPN/main/install.sh) reset [COMMIT_OR_BRANCH]
#
# 2. Локальный запуск (если репозиторий уже установлен и нужно просто обновить/сбросить):
# bash install.sh update [COMMIT_OR_BRANCH]
# bash install.sh reset [COMMIT_OR_BRANCH]

set -e

INSTALL_DIR="/root/YadrenoVPN"
REPO_URL="https://github.com/heratxd/YadrenoVPN.git"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_FILE="yadreno-vpn.service"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Поиск и отключение старого бота
cleanup_old_bot_install() {
    print_header "Поиск и отключение старых версий бота"

    # Находим все службы в /etc/systemd/system/, которые могут относиться к боту
    local found_services=()
    
    # 1. Поиск по стандартным именам
    for svc in "yadreno-vpn" "yadreno" "vpn-bot" "tg-vpn-bot" "vpn_bot"; do
        if [ -f "/etc/systemd/system/${svc}.service" ]; then
            found_services+=("${svc}.service")
        fi
    done

    # 2. Ищем по содержимому файлов служб в /etc/systemd/system/
    for svc_file in /etc/systemd/system/*.service; do
        if [ -f "$svc_file" ]; then
            local fname=$(basename "$svc_file")
            # Проверяем, не добавили ли уже
            if [[ ! " ${found_services[@]} " =~ " ${fname} " ]]; then
                if grep -E -q "ExecStart=.*(python|venv).*/main\.py" "$svc_file" || grep -q "yadreno" "$svc_file" || (grep -q "main.py" "$svc_file" && grep -q "vpn" "$svc_file"); then
                    found_services+=("$fname")
                fi
            fi
        fi
    done

    # 3. Обрабатываем каждую найденную службу
    if [ ${#found_services[@]} -gt 0 ]; then
        print_warn "Обнаружены потенциально старые службы бота: ${found_services[*]}"
        
        for old_svc in "${found_services[@]}"; do
            print_warn "Обработка службы: $old_svc"
            
            # Получаем директорию из WorkingDirectory
            local old_dir=""
            old_dir=$(grep -oP "WorkingDirectory=\K.*" "/etc/systemd/system/$old_svc" 2>/dev/null | tr -d '\r' || true)
            
            if [ -n "$old_dir" ] && [ -d "$old_dir" ]; then
                print_ok "Рабочая директория старого бота: $old_dir"
                
                # Резервное копирование старого конфига
                if [ -f "$old_dir/config.py" ]; then
                    cp "$old_dir/config.py" /tmp/yadreno_old_config.py
                    print_ok "Старый config.py скопирован в /tmp/yadreno_old_config.py"
                fi
                
                # Резервное копирование базы данных (SQLite)
                if [ -f "$old_dir/database/vpn_bot.db" ]; then
                    cp "$old_dir/database/vpn_bot.db" /tmp/yadreno_old_db.db
                    print_ok "База данных скопирована из $old_dir/database/"
                elif [ -f "$old_dir/vpn_bot.db" ]; then
                    cp "$old_dir/vpn_bot.db" /tmp/yadreno_old_db.db
                    print_ok "База данных скопирована из $old_dir"
                fi
            fi

            # Останавливаем и отключаем службу
            print_warn "Убиваем процессы и отключаем службу: $old_svc"
            systemctl stop "$old_svc" 2>/dev/null || true
            systemctl disable "$old_svc" 2>/dev/null || true
            rm -f "/etc/systemd/system/$old_svc"
            print_ok "Служба $old_svc удалена"
        done
        
        systemctl daemon-reload
    else
        print_ok "Активных старых служб бота в systemd не найдено"
    fi

    # 4. Убиваем все процессы python, которые запускают main.py (кроме тех, которые запущены из /tmp)
    local pids=$(pgrep -f "python.*main\.py" || true)
    if [ -n "$pids" ]; then
        print_warn "Найдены запущенные процессы бота (PIDs: $pids). Завершаем их..."
        for pid in $pids; do
            # Проверяем, не является ли это текущим скриптом или процессом установки/тестирования из /tmp
            local cmdline=$(cat /proc/$pid/cmdline 2>/dev/null | tr '\0' ' ' || true)
            if [[ ! "$cmdline" =~ "/tmp/" ]]; then
                print_warn "Убиваем процесс PID $pid: $cmdline"
                kill -9 "$pid" 2>/dev/null || true
            fi
        done
    fi
}

# Функция слияния конфигураций
merge_old_config() {
    local source_config=""
    if [ -f "/tmp/yadreno_old_config.py" ]; then
        source_config="/tmp/yadreno_old_config.py"
    elif [ -f "/tmp/yadreno_config_backup.py" ]; then
        source_config="/tmp/yadreno_config_backup.py"
    fi

    if [ -n "$source_config" ] && [ -f "$INSTALL_DIR/config.py" ]; then
        print_header "Миграция настроек config.py"
        
        # Создаем временный python-скрипт слияния на основе AST
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

# Вытаскиваем только переменные настроек (в верхнем регистре)
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
                    if isinstance(val, str):
                        formatted_val = f'"{val}"'
                    else:
                        formatted_val = repr(val)
                    new_text = f"{var_name} = {formatted_val}"
                    replacements.append((node.lineno, node.end_lineno, new_text))
                    replaced_keys.add(var_name)

# Применяем замены в обратном порядке строк
replacements.sort(key=lambda x: x[0], reverse=True)
for start, end, new_text in replacements:
    lines[start-1:end] = [new_text + '\n']

# Добавляем переменные, которых не было в новом шаблоне
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
    print("✅ Настройки из старого config.py успешно перенесены!")
except Exception as e:
    print(f"Ошибка записи нового конфига: {e}")
    sys.exit(1)
EOF

        python3 /tmp/migrate_config.py "$source_config" "$INSTALL_DIR/config.py"
        rm -f /tmp/migrate_config.py
        rm -f /tmp/yadreno_old_config.py
        rm -f /tmp/yadreno_config_backup.py
    fi
}

# Запрос настроек у пользователя
ask_config() {
    print_header "Настройка конфигурации"

    if [ "$AUTO_MODE" = "1" ]; then
        NEED_WRITE_CONFIG=1
        print_ok "Автоматический режим: используем переданные параметры"
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
        read -p "ADMIN_IDS (ваш Telegram ID): " admin_id
        if [ -n "$admin_id" ] && [[ "$admin_id" =~ ^[0-9]+$ ]]; then
            break
        fi
        print_err "ADMIN_IDS должен быть числом!"
    done

    BOT_TOKEN="$bot_token"
    ADMIN_ID="$admin_id"
    NEED_WRITE_CONFIG=1
    print_ok "Данные получены"
}

# Создание/обновление config.py
write_config() {
    if [ "$NEED_WRITE_CONFIG" != "1" ]; then
        return 0
    fi

    cp "$INSTALL_DIR/config.py.example" "$INSTALL_DIR/config.py"

    sed -i "s|\"ВАШ_ТОКЕН_БОТА\"|\"$BOT_TOKEN\"|g" "$INSTALL_DIR/config.py"
    sed -i "s|12345678|$ADMIN_ID|g" "$INSTALL_DIR/config.py"

    # Настройки PostgreSQL
    sed -i "s|DB_TYPE = \"sqlite\"|DB_TYPE = \"postgres\"|g" "$INSTALL_DIR/config.py"
    sed -i "s|PG_PASSWORD = \"yadreno_pass\"|PG_PASSWORD = \"$PG_PASS\"|g" "$INSTALL_DIR/config.py"

    print_ok "config.py создан с вашими настройками"
}

# Установка системных пакетов
install_system_deps() {
    print_header "Установка системных зависимостей"

    export DEBIAN_FRONTEND=noninteractive
    export NEEDRESTART_MODE=a

    apt-get update -qq
    apt-get install -y -qq \
        python3-venv \
        python3-pip \
        git \
        postgresql \
        postgresql-contrib \
        > /dev/null 2>&1

    # Запуск и автозапуск PostgreSQL службы
    systemctl start postgresql || true
    systemctl enable postgresql || true

    print_ok "Системные пакеты обновлены"
    print_ok "python3-venv, python3-pip, git, postgresql установлены"
}

# Настройка PostgreSQL
setup_postgresql() {
    print_header "Настройка локального PostgreSQL"

    # Проверяем, запущен ли PostgreSQL
    if ! systemctl is-active --quiet postgresql; then
        systemctl start postgresql || true
        sleep 2
    fi

    # Генерация случайного пароля, если его ещё нет
    if [ -f "$INSTALL_DIR/config.py" ]; then
        PG_PASS=$(grep -oP "PG_PASSWORD = '\K[^']+" "$INSTALL_DIR/config.py" 2>/dev/null || grep -oP 'PG_PASSWORD = "\K[^"]+' "$INSTALL_DIR/config.py" 2>/dev/null || true)
    fi
    if [ -z "$PG_PASS" ]; then
        PG_PASS=$(openssl rand -hex 16 2>/dev/null || echo "yadreno_secure_pass_$(date +%s)")
    fi

    # Создание пользователя и БД
    sudo -u postgres psql -c "CREATE USER yadreno_user WITH PASSWORD '$PG_PASS';" >/dev/null 2>&1 || true
    sudo -u postgres psql -c "ALTER USER yadreno_user WITH PASSWORD '$PG_PASS';" >/dev/null 2>&1 || true
    sudo -u postgres psql -c "CREATE DATABASE yadreno_vpn OWNER yadreno_user;" >/dev/null 2>&1 || true
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE yadreno_vpn TO yadreno_user;" >/dev/null 2>&1 || true

    print_ok "База данных yadreno_vpn и пользователь yadreno_user настроены"
}


# Создание виртуального окружения и установка зависимостей
setup_venv() {
    print_header "Настройка виртуального окружения Python"

    python3 -m venv "$VENV_DIR"
    print_ok "Виртуальное окружение создано: $VENV_DIR"

    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip -q
    pip install --upgrade -r "$INSTALL_DIR/requirements.txt" -q
    deactivate

    print_ok "Зависимости Python установлены в venv"
}

# Настройка systemd сервиса
setup_systemd() {
    print_header "Настройка автозапуска (systemd)"

    cat > "$INSTALL_DIR/$SERVICE_FILE" << EOF
[Unit]
Description=Yadreno VPN Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    cp "$INSTALL_DIR/$SERVICE_FILE" /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable yadreno-vpn > /dev/null 2>&1

    print_ok "systemd сервис установлен и включён в автозапуск"
}

# Запуск сервиса
start_service() {
    systemctl start yadreno-vpn
    sleep 2

    if systemctl is-active --quiet yadreno-vpn; then
        print_ok "Бот запущен и работает!"
    else
        print_err "Бот не запустился. Проверьте логи:"
        echo "  systemctl status yadreno-vpn"
        echo "  journalctl -u yadreno-vpn -n 50"
    fi
}

# ============================================================
# ПУНКТ 1: УСТАНОВКА
# ============================================================
do_install() {
    print_header "🚀 Установка Yadreno VPN"

    # Ищем и отключаем старые версии бота перед установкой
    cleanup_old_bot_install

    # Проверяем, не установлен ли уже в целевой каталог
    if [ -d "$INSTALL_DIR" ] && [ -d "$INSTALL_DIR/.git" ]; then
        print_warn "Yadreno VPN уже установлен в $INSTALL_DIR"
        if [ "$AUTO_MODE" = "1" ]; then
            print_warn "Автоматический режим: принудительная переустановка"
            reinstall_choice="1"
        else
            echo ""
            echo "  1) Переустановить (удалить и установить заново)"
            echo "  2) Отмена"
            read -p "Выберите [1-2]: " reinstall_choice
        fi
        if [ "$reinstall_choice" != "1" ]; then
            echo "Установка отменена."
            return 0
        fi
        systemctl stop yadreno-vpn 2>/dev/null || true
        # Сохраняем config.py и базу данных
        if [ -f "$INSTALL_DIR/config.py" ]; then
            cp "$INSTALL_DIR/config.py" /tmp/yadreno_config_backup.py
            BACKUP_CONFIG=1
        fi
        if [ -f "$INSTALL_DIR/vpn_bot.db" ]; then
            cp "$INSTALL_DIR/vpn_bot.db" /tmp/yadreno_db_backup.db
            BACKUP_DB=1
        fi
        rm -rf "$INSTALL_DIR"
    fi

    # Запрашиваем настройки до начала установки
    ask_config

    # Установка системных зависимостей
    install_system_deps

    # Клонирование репозитория
    print_header "Загрузка Yadreno VPN"
    git clone "$REPO_URL" "$INSTALL_DIR" -q
    cd "$INSTALL_DIR"
    print_ok "Репозиторий клонирован"

    # Восстановление backup'ов при переустановке
    if [ "$BACKUP_CONFIG" = "1" ] && [ -f "/tmp/yadreno_config_backup.py" ]; then
        cp /tmp/yadreno_config_backup.py "$INSTALL_DIR/config.py"
        rm /tmp/yadreno_config_backup.py
        print_ok "config.py восстановлен из резервной копии"
        NEED_WRITE_CONFIG=0
    fi
    if [ "$BACKUP_DB" = "1" ] && [ -f "/tmp/yadreno_db_backup.db" ]; then
        mkdir -p "$INSTALL_DIR/database"
        cp /tmp/yadreno_db_backup.db "$INSTALL_DIR/database/vpn_bot.db"
        rm /tmp/yadreno_db_backup.db
        print_ok "База данных восстановлена из резервной копии"
    fi

    # Восстановление базы данных старого бота
    if [ -f "/tmp/yadreno_old_db.db" ]; then
        mkdir -p "$INSTALL_DIR/database"
        cp /tmp/yadreno_old_db.db "$INSTALL_DIR/database/vpn_bot.db"
        rm -f "/tmp/yadreno_old_db.db"
        print_ok "База данных старого бота перенесена в новый бот"
    fi

    # Настройка PostgreSQL
    setup_postgresql

    # Запись config.py
    write_config

    # Слияние настроек старого config.py с новым шаблоном
    merge_old_config

    # Виртуальное окружение и зависимости
    setup_venv

    # Настройка автозапуска
    setup_systemd

    # Запуск
    print_header "Запуск бота"
    start_service

    print_header "✅ Установка завершена!"
    echo -e "  Директория: ${GREEN}$INSTALL_DIR${NC}"
    echo -e "  Виртуальное окружение: ${GREEN}$VENV_DIR${NC}"
    echo -e "  Управление сервисом:"
    echo -e "    ${CYAN}systemctl status yadreno-vpn${NC}   — статус"
    echo -e "    ${CYAN}systemctl restart yadreno-vpn${NC}  — перезапуск"
    echo -e "    ${CYAN}systemctl stop yadreno-vpn${NC}     — остановка"
    echo -e "    ${CYAN}journalctl -u yadreno-vpn -f${NC}   — логи"
}

# ============================================================
# ПУНКТ 2: МЯГКОЕ ОБНОВЛЕНИЕ (git pull)
# ============================================================
do_soft_update() {
    print_header "🔄 Мягкое обновление"

    if [ ! -d "$INSTALL_DIR/.git" ]; then
        print_err "Yadreno VPN не установлен в $INSTALL_DIR"
        return 1
    fi

    cd "$INSTALL_DIR"

    # Сохраняем текущие изменения в stash (если есть)
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        print_warn "Обнаружены локальные изменения — сохраняем через git stash"
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
        git stash pop -q 2>/dev/null || print_warn "Не удалось восстановить локальные изменения (конфликт)"
    fi

    print_ok "Код обновлён"

    # Обновляем зависимости
    source "$VENV_DIR/bin/activate"
    pip install --upgrade -r requirements.txt -q
    deactivate
    print_ok "Зависимости обновлены"

    # Перезапуск
    systemctl restart yadreno-vpn
    sleep 2

    if systemctl is-active --quiet yadreno-vpn; then
        print_ok "Бот перезапущен и работает!"
    else
        print_err "Бот не запустился после обновления"
        echo "  systemctl status yadreno-vpn"
    fi
}

# ============================================================
# ПУНКТ 3: ЖЁСТКАЯ ПЕРЕЗАПИСЬ (git fetch + reset)
# ============================================================
do_hard_reset() {
    print_header "⚠️  Жёсткая перезапись"

    if [ ! -d "$INSTALL_DIR/.git" ]; then
        print_err "Yadreno VPN не установлен в $INSTALL_DIR"
        return 1
    fi

    echo -e "${RED}Внимание! Все локальные изменения в коде будут перезаписаны.${NC}"
    echo -e "${YELLOW}config.py и vpn_bot.db затронуты НЕ будут.${NC}"
    if [ "$AUTO_MODE" = "1" ]; then
        confirm="y"
    else
        read -p "Продолжить? (y/N): " confirm
    fi
    if [[ ! "$confirm" =~ ^[YyДд]$ ]]; then
        echo "Отменено."
        return 0
    fi

    cd "$INSTALL_DIR"

    # Жёсткая перезапись: config.py и vpn_bot.db в .gitignore — не затрагиваются
    git fetch origin -q
    local target="origin/main"
    if [ -n "$TARGET_COMMIT" ]; then
        target="$TARGET_COMMIT"
    fi
    git reset --hard "$target" -q
    git clean -fd -q
    print_ok "Код перезаписан ($target)"

    # Обновляем зависимости
    source "$VENV_DIR/bin/activate"
    pip install --upgrade -r requirements.txt -q
    deactivate
    print_ok "Зависимости обновлены"

    # Перезапуск
    systemctl restart yadreno-vpn
    sleep 2

    if systemctl is-active --quiet yadreno-vpn; then
        print_ok "Бот перезапущен и работает!"
    else
        print_err "Бот не запустился после перезаписи"
        echo "  systemctl status yadreno-vpn"
    fi
}

# ============================================================
# ГЛАВНОЕ МЕНЮ
# ============================================================
show_menu() {
    clear
    echo -e "${CYAN}"
    echo "  ╔═══════════════════════════════════════╗"
    echo "  ║       🌐 Yadreno VPN Manager         ║"
    echo "  ╚═══════════════════════════════════════╝"
    echo -e "${NC}"
    echo "  1) 🚀 Установка"
    echo "  2) 🔄 Мягкое обновление (git pull)"
    echo "  3) ⚠️  Жёсткая перезапись (с GitHub)"
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
    print_err "Скрипт должен быть запущен от root (sudo)"
    exit 1
fi

# Проверка на автоматический режим (передан аргумент действия)
if [ -n "$1" ]; then
    ACTION="$1"
    export AUTO_MODE="1"
    
    case "$ACTION" in
        install)
            if [ -z "$2" ] || [ -z "$3" ]; then
                print_err "Для автоматической установки требуются BOT_TOKEN и ADMIN_ID"
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
            print_err "Неизвестное действие: $ACTION. Доступно: install, update, reset"
            exit 1
            ;;
    esac
    exit 0
fi

show_menu
