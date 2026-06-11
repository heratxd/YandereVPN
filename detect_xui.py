#!/usr/bin/env python3
import os
import sys
import sqlite3
import urllib.request
import json

# Добавляем текущую директорию в sys.path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database.migrations import run_migrations
from database.connection import get_db

def get_public_ip():
    """Получает публичный IP сервера."""
    urls = [
        "https://api.ipify.org?format=json",
        "https://ifconfig.me/ip",
        "https://ipinfo.io/ip",
        "https://ident.me"
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_text = response.read().decode('utf-8').strip()
                if "{" in resp_text:
                    data = json.loads(resp_text)
                    return data.get("ip", "127.0.0.1")
                return resp_text
        except Exception:
            continue
    return "127.0.0.1"

def check_local_xui():
    """Проверяет наличие локальной панели 3x-ui по стандартным путям."""
    paths = [
        "/etc/x-ui/x-ui.db",
        "/usr/local/x-ui/bin/x-ui.db"
    ]
    for path in paths:
        if os.path.exists(path):
            return path
    return None

def extract_xui_settings(db_path):
    """Извлекает настройки из базы данных 3x-ui."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем пользователя (обычно первая строка)
        cursor.execute("SELECT username FROM users LIMIT 1")
        user_row = cursor.fetchone()
        username = user_row['username'] if user_row else "admin"
        
        # Получаем настройки
        cursor.execute("SELECT key, value FROM settings")
        settings = {row['key']: row['value'] for row in cursor.fetchall()}
        
        port = settings.get("webPort", 2053)
        web_base_path = settings.get("webBasePath", "/")
        if not web_base_path.startswith("/"):
            web_base_path = "/" + web_base_path
        if not web_base_path.endswith("/"):
            web_base_path = web_base_path + "/"
            
        cert_file = settings.get("webCertFile", "")
        protocol = "https" if cert_file else "http"
        
        conn.close()
        return {
            "username": username,
            "port": int(port),
            "web_base_path": web_base_path,
            "protocol": protocol
        }
    except Exception as e:
        print(f"Ошибка при чтении базы данных 3x-ui: {e}")
        return None

def link_server_to_bot(settings, password):
    """Добавляет или обновляет сервер в базе данных бота."""
    try:
        # Убедимся, что таблицы созданы
        run_migrations()
        
        public_ip = get_public_ip()
        
        with get_db() as conn:
            # Проверяем, существует ли уже сервер с таким хостом
            cursor = conn.execute("SELECT id FROM servers WHERE host = ?", (public_ip,))
            row = cursor.fetchone()
            
            if row:
                server_id = row['id']
                conn.execute(
                    """
                    UPDATE servers 
                    SET name = ?, port = ?, web_base_path = ?, login = ?, password = ?, protocol = ?, is_active = 1
                    WHERE id = ?
                    """,
                    (
                        "Локальный 3x-ui",
                        settings["port"],
                        settings["web_base_path"],
                        settings["username"],
                        password,
                        settings["protocol"],
                        server_id
                    )
                )
                print(f"\n✅ Настройки сервера (ID: {server_id}) успешно обновлены в базе данных бота!")
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO servers (name, host, port, web_base_path, login, password, protocol, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        "Локальный 3x-ui",
                        public_ip,
                        settings["port"],
                        settings["web_base_path"],
                        settings["username"],
                        password,
                        settings["protocol"]
                    )
                )
                print(f"\n✅ Сервер успешно добавлен в базу данных бота под ID {cursor.lastrowid}!")
        return True
    except Exception as e:
        print(f"\n❌ Ошибка при привязке сервера к боту: {e}")
        return False

def main():
    print("==================================================")
    print("🔍 Автоопределение локальной панели 3x-ui...")
    print("==================================================")
    
    db_path = check_local_xui()
    
    if not db_path:
        print("\nℹ️ Локальная панель 3x-ui не обнаружена на этом сервере (или не примонтирована).")
        print("Связывание пропущено. Вы можете настроить панель вручную через админку бота.")
        sys.exit(0)
            
    # Если панель найдена
    settings = extract_xui_settings(db_path)
    if not settings:
        print("\n❌ Не удалось прочесть настройки из базы данных 3x-ui.")
        sys.exit(1)
        
    public_ip = get_public_ip()
    
    print("\n✨ Обнаружена локальная панель 3x-ui!")
    print(f"  🌐 Хост (IP): {public_ip}")
    print(f"  🔌 Порт: {settings['port']}")
    print(f"  📂 Путь API: {settings['web_base_path']}")
    print(f"  👤 Логин: {settings['username']}")
    print(f"  🔒 Протокол: {settings['protocol'].upper()}")
    
    # Спрашиваем пользователя
    sys.stdout.write("\nХотите автоматически привязать эту панель к вашему боту? (Y/n): ")
    sys.stdout.flush()
    ans = sys.stdin.readline().strip().lower()
    
    if ans in ('', 'y'):
        sys.stdout.write(f"Пожалуйста, введите пароль для пользователя '{settings['username']}' от панели 3x-ui: ")
        sys.stdout.flush()
        password = sys.stdin.readline().strip()
        
        if not password:
            print("❌ Пароль не может быть пустым.")
            sys.exit(1)
            
        link_server_to_bot(settings, password)
    else:
        print("\nСвязывание отменено. Вы можете настроить панель позже через интерфейс админа в Telegram.")

if __name__ == "__main__":
    main()
