import os
import threading
import time
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# 🔑 Секретный ключ. На Render добавь его в Environment Variables!
# Локально можно задать через set API_KEY=... или оставить dev-ключ для теста.
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    API_KEY = "dev-local-key-change-me"
    print("[WARN] API_KEY не задан! Используется dev-ключ только для локального теста.")

# Временное хранилище (в памяти).
players_db = {}


# --- ЗАПИСЬ (только с ключом) ---
@app.route('/update', methods=['POST'])
def update_position():
    """Roblox шлёт сюда свою позицию. Только с правильным ключом."""
    key = request.headers.get("X-Api-Key")
    if key != API_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "name" not in data or "cframe" not in data:
        return jsonify({"error": "Bad data"}), 400

    players_db[data["name"]] = data["cframe"]
    return jsonify({"status": "ok"}), 200


# --- ЧТЕНИЕ (публичное) ---
@app.route('/state', methods=['GET'])
def get_state():
    """Любой может читать позиции игроков."""
    return jsonify({"players": players_db}), 200


# --- HTML-СТРАНИЦА ДЛЯ ПРОСМОТРА ---
HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Roblox Bridge — Live</title>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="2">
    <style>
        body { font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }
        h1 { color: #4ec9b0; }
        .player { background: #252526; padding: 10px; margin: 8px 0; border-radius: 6px; border-left: 3px solid #4ec9b0; }
        .name { color: #dcdcaa; font-weight: bold; }
        .coords { color: #9cdcfe; }
        .empty { color: #808080; font-style: italic; }
        .count { color: #ce9178; }
    </style>
</head>
<body>
    <h1>🌉 Roblox Bridge</h1>
    <p>Игроков онлайн: <span class="count">{{ count }}</span></p>
    {% if players %}
        {% for name, cf in players.items() %}
            <div class="player">
                <div class="name">👤 {{ name }}</div>
                <div class="coords">
                    pos: ({{ "%.1f"|format(cf.x) }}, {{ "%.1f"|format(cf.y) }}, {{ "%.1f"|format(cf.z) }})
                </div>
            </div>
        {% endfor %}
    {% else %}
        <p class="empty">Пока никого нет...</p>
    {% endif %}
</body>
</html>
"""


@app.route('/', methods=['GET'])
def index():
    """Красивая страница с позициями игроков."""
    return render_template_string(HTML_PAGE, players=players_db, count=len(players_db))


@app.route('/ping', methods=['GET'])
def ping():
    """Keep-alive эндпоинт."""
    return "pong", 200


# --- KEEP ALIVE ---
def keep_alive_ping():
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        print("[KeepAlive] Нет RENDER_EXTERNAL_URL, пингер не запущен.")
        return

    ping_url = f"{url}/ping"
    while True:
        time.sleep(100)  # не 14 минут
        try:
            import requests
            r = requests.get(ping_url, timeout=10)
            print(f"[KeepAlive] Пинг: {r.status_code}")
        except Exception as e:
            print(f"[KeepAlive] Ошибка: {e}")


# Запускаем пингер и локально, и под gunicorn (там __main__ не выполняется)
threading.Thread(target=keep_alive_ping, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
