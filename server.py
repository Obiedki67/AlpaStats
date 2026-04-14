import json
import os
from flask import Flask, jsonify, request, render_template_string
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 20003))
DATA_FILE = "players_data.json"
SUPPORT_FILE = "support_requests.json"
MAINTENANCE_FILE = "maintenance_mode.json"

# ========== ИНИЦИАЛИЗАЦИЯ ФАЙЛОВ ==========
def init_files():
    # Данные игроков
    if not os.path.exists(DATA_FILE):
        default_data = {
            "players": {
                "Alpa": {"kills": 0, "wins": 0, "defeats": 0, "deaths": 0, "xp": 0}
            },
            "top_positions": {str(i): None for i in range(1, 11)}
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
    
    # Обращения в поддержку
    if not os.path.exists(SUPPORT_FILE):
        with open(SUPPORT_FILE, "w") as f:
            json.dump([], f, indent=4)
    
    # Режим техобслуживания
    if not os.path.exists(MAINTENANCE_FILE):
        with open(MAINTENANCE_FILE, "w") as f:
            json.dump({"maintenance": False}, f, indent=4)

init_files()

def load_data():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_support():
    with open(SUPPORT_FILE, "r") as f:
        return json.load(f)

def save_support(requests_list):
    with open(SUPPORT_FILE, "w") as f:
        json.dump(requests_list, f, indent=4)

def get_maintenance_mode():
    with open(MAINTENANCE_FILE, "r") as f:
        return json.load(f).get("maintenance", False)

def set_maintenance_mode(enabled):
    with open(MAINTENANCE_FILE, "w") as f:
        json.dump({"maintenance": enabled}, f, indent=4)

# ========== API ДЛЯ САЙТА ==========
@app.route('/')
def home():
    return "Alpa API is running 🚀"

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route("/api/maintenance", methods=["GET"])
def get_maintenance():
    return jsonify({"maintenance": get_maintenance_mode()})

@app.route("/api/top", methods=["GET"])
def get_top():
    data = load_data()
    players = data["players"]
    stats_list = []
    for name, stat in players.items():
        stats_list.append({
            "name": name,
            "kills": stat.get("kills", 0),
            "wins": stat.get("wins", 0),
            "defeats": stat.get("defeats", 0),
            "deaths": stat.get("deaths", 0),
            "xp": stat.get("xp", 0)
        })
    categories = ["kills", "wins", "defeats", "deaths", "xp"]
    result = {}
    for cat in categories:
        sorted_list = sorted(stats_list, key=lambda x: x[cat], reverse=True)
        result[cat] = []
        for i in range(10):
            if i < len(sorted_list):
                result[cat].append({"name": sorted_list[i]["name"], "value": sorted_list[i][cat]})
            else:
                result[cat].append({"name": "—", "value": "—"})
    return jsonify(result)

# ========== ЧАТ ПОДДЕРЖКИ ==========
@app.route("/api/support/send", methods=["POST"])
def send_support():
    req = request.json
    name = req.get("name", "Аноним")
    message = req.get("message", "").strip()
    if not message:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400
    
    support_list = load_support()
    new_request = {
        "id": len(support_list) + 1,
        "name": name,
        "message": message,
        "status": "new",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "answer": None,
        "answered_at": None
    }
    support_list.append(new_request)
    save_support(support_list)
    return jsonify({"success": True, "id": new_request["id"]})

@app.route("/api/support/my", methods=["POST"])
def get_my_requests():
    req = request.json
    name = req.get("name", "")
    if not name:
        return jsonify([])
    support_list = load_support()
    my_requests = [r for r in support_list if r["name"] == name]
    return jsonify(my_requests)

# ========== АДМИН-ПАНЕЛЬ ДЛЯ ОТВЕТОВ ==========
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        action = request.form.get("action")
        
        # Команды /teh и /unteh
        if action == "teh":
            set_maintenance_mode(True)
            return '<pre>🔧 Режим технического обслуживания ВКЛЮЧЁН. Сайт будет показывать ⚪</pre><a href="/admin">← Назад</a>'
        elif action == "unteh":
            set_maintenance_mode(False)
            return '<pre>✅ Режим технического обслуживания ВЫКЛЮЧЁН. Сайт работает нормально.</pre><a href="/admin">← Назад</a>'
        
        # Ответ на обращение
        elif action == "answer":
            req_id = int(request.form.get("req_id"))
            answer = request.form.get("answer", "").strip()
            if answer:
                support_list = load_support()
                for r in support_list:
                    if r["id"] == req_id:
                        r["answer"] = answer
                        r["status"] = "answered"
                        r["answered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        break
                save_support(support_list)
                return '<pre>✅ Ответ сохранён</pre><a href="/admin">← Назад</a>'
        
        # Обычная команда /set и т.д.
        else:
            cmd = request.form.get("command", "").strip()
            if cmd:
                result = run_command_internal(cmd)
                return f'<pre>{result}</pre><a href="/admin">← Назад</a>'
    
    # GET — показываем админ-панель
    maintenance = get_maintenance_mode()
    support_list = load_support()
    unanswered = [r for r in support_list if r["status"] == "new"]
    answered = [r for r in support_list if r["status"] == "answered"]
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alpa Server Admin</title>
        <style>
            body{background:#0a0a0a;color:#eee;font-family:monospace;padding:20px;}
            h1,h2{color:#ff6b5c;}
            .section{background:#111;border:1px solid #2c2c2c;border-radius:16px;padding:15px;margin-bottom:20px;}
            input,textarea{background:#1a1a1a;border:1px solid #333;color:white;padding:8px;width:100%;margin-bottom:10px;border-radius:8px;}
            button{background:#ff6b5c;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-weight:bold;}
            .request{background:#1a1a1a;border-left:3px solid #ff6b5c;padding:10px;margin-bottom:10px;}
            .answered{opacity:0.7;border-left-color:#6bff6b;}
            hr{border-color:#2c2c2c;}
            .maintenance-on{background:#ff6b5c20;padding:5px;border-radius:8px;color:#ff6b5c;}
        </style>
    </head>
    <body>
        <h1>🔧 Админ-панель</h1>
        
        <div class="section">
            <h2>🛠 Режим техобслуживания</h2>
            <p>Текущий статус: <strong>{% if maintenance %}⚠️ ВКЛЮЧЁН (сайт показывает ⚪){% else %}✅ ВЫКЛЮЧЁН (сайт работает){% endif %}</strong></p>
            <form method="post" style="display:inline-block;">
                <input type="hidden" name="action" value="teh">
                <button type="submit" style="background:#ff6b5c;">🔧 Включить /teh</button>
            </form>
            <form method="post" style="display:inline-block;margin-left:10px;">
                <input type="hidden" name="action" value="unteh">
                <button type="submit" style="background:#6bff6b;color:#0a0a0a;">✅ Выключить /unteh</button>
            </form>
        </div>
        
        <div class="section">
            <h2>📋 Команды сервера</h2>
            <form method="post">
                <input type="text" name="command" placeholder="/set Alpa kills 10" style="width:70%;">
                <button type="submit">Отправить</button>
            </form>
            <p>Примеры: /set Fr0st kills 100, /settop 1 Alpa, /tops, /untop Fr0st</p>
        </div>
        
        <div class="section">
            <h2>💬 Обращения в поддержку ({{ unanswered|length }} новых)</h2>
            {% for req in unanswered %}
            <div class="request">
                <strong>#{{ req.id }}</strong> от <strong>{{ req.name }}</strong> ({{ req.created_at }})<br>
                <em>Сообщение:</em> {{ req.message }}<br>
                <form method="post" style="margin-top:10px;">
                    <input type="hidden" name="action" value="answer">
                    <input type="hidden" name="req_id" value="{{ req.id }}">
                    <input type="text" name="answer" placeholder="Ваш ответ..." style="width:70%;">
                    <button type="submit">Ответить</button>
                </form>
            </div>
            {% else %}
            <p>✅ Нет новых обращений</p>
            {% endfor %}
        </div>
        
        <div class="section">
            <h2>📜 Отвеченные обращения</h2>
            {% for req in answered %}
            <div class="request answered">
                <strong>#{{ req.id }}</strong> от <strong>{{ req.name }}</strong><br>
                <em>Вопрос:</em> {{ req.message }}<br>
                <em style="color:#6bff6b;">Ответ:</em> {{ req.answer }} ({{ req.answered_at }})
            </div>
            {% else %}
            <p>Нет отвеченных обращений</p>
            {% endfor %}
        </div>
        
        <p><a href="/api/top" target="_blank">📡 Посмотреть JSON</a></p>
    </body>
    </html>
    ''', maintenance=maintenance, unanswered=unanswered, answered=answered)

# ========== ВНУТРЕННИЕ КОМАНДЫ ==========
def run_command_internal(cmd_line):
    parts = cmd_line.strip().split()
    if not parts:
        return "Пустая команда"
    
    cmd = parts[0].lower()
    data = load_data()
    
    if cmd == "/set" and len(parts) >= 4:
        name, stat, val = parts[1], parts[2].lower(), parts[3]
        try:
            val = int(val)
        except:
            return "❌ Значение должно быть числом"
        if stat not in ["kills","wins","defeats","deaths","xp"]:
            return "❌ Статы: kills, wins, defeats, deaths, xp"
        if name not in data["players"]:
            data["players"][name] = {"kills":0,"wins":0,"defeats":0,"deaths":0,"xp":0}
        data["players"][name][stat] = val
        save_data(data)
        return f"✅ {name}: {stat} = {val}"
    
    elif cmd == "/settop" and len(parts) >= 3:
        place, name = parts[1], parts[2]
        if place not in [str(i) for i in range(1,11)]:
            return "❌ Место от 1 до 10"
        if name not in data["players"]:
            return f"❌ Игрок {name} не найден"
        data["top_positions"][place] = name
        save_data(data)
        return f"🏆 {name} закреплён на {place} месте"
    
    elif cmd == "/tops":
        players = data["players"]
        if not players:
            return "📭 Нет игроков"
        sorted_players = sorted(players.items(), key=lambda x: x[1].get("xp",0), reverse=True)
        lines = ["🏅 ТОП-10 по опыту:"]
        for i, (name, stat) in enumerate(sorted_players[:10], 1):
            lines.append(f"{i}. {name} — опыт: {stat.get('xp',0)}")
        return "\n".join(lines)
    
    elif cmd == "/untop" and len(parts) >= 2:
        name = parts[1]
        removed = False
        for place, player in data["top_positions"].items():
            if player == name:
                data["top_positions"][place] = None
                removed = True
        if removed:
            save_data(data)
            return f"🗑 {name} удалён из топа"
        return f"❌ {name} не найден"
    
    else:
        return "❌ Доступно: /set, /settop, /tops, /untop"

@app.route("/api/command", methods=["POST"])
def run_command_api():
    req = request.json
    cmd_line = req.get("command", "").strip()
    result = run_command_internal(cmd_line)
    return jsonify({"result": result})

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print(f"🚀 Сервер запущен на порту {PORT}")
    print(f"📡 API: /api/top")
    print(f"🔧 Админ-панель: /admin")
    print(f"💬 Команды: /teh (техобслуживание), /unteh (выключить)")
    app.run(host="0.0.0.0", port=PORT, debug=False)
