import json
import os
import time
from flask import Flask, jsonify, request, render_template_string, make_response
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 20003))
DATA_FILE = "players_data.json"
SUPPORT_FILE = "support_requests.json"
MAINTENANCE_FILE = "maintenance_mode.json"
POSTS_FILE = "posts.json"
BANNED_FILE = "banned_users.json"
USERS_FILE = "registered_users.json"

# ========== ЕДИНЫЙ ПАРОЛЬ ДЛЯ АДМИН-ПАНЕЛИ ==========
ADMIN_PASSWORD_HASH = "b8e3f2a1c9d4e5f6a7b8c9d0e1f2a3b4"  # Хеш пароля
def simple_hash(s):
    hash_val = 0
    for c in s:
        hash_val = ((hash_val << 5) - hash_val) + ord(c)
        hash_val &= 0xFFFFFFFF
    return hex(hash_val)[2:]

# ========== ИНИЦИАЛИЗАЦИЯ ФАЙЛОВ ==========
def init_files():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "players": {
                "Alpa": {"kills": 0, "wins": 0, "defeats": 0, "deaths": 0, "xp": 0}
            },
            "top_positions": {str(i): None for i in range(1, 11)}
        }
        with open(DATA_FILE, "w") as f:
            json.dump(default_data, f, indent=4)
    
    if not os.path.exists(SUPPORT_FILE):
        with open(SUPPORT_FILE, "w") as f:
            json.dump([], f, indent=4)
    
    if not os.path.exists(MAINTENANCE_FILE):
        with open(MAINTENANCE_FILE, "w") as f:
            json.dump({"maintenance": False}, f, indent=4)
    
    if not os.path.exists(POSTS_FILE):
        default_posts = [
            {
                "id": 1,
                "title": "💬 Чат поддержки",
                "content": "Теперь вы можете отправить вопрос администратору. Не спамьте, пожалуйста!",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "author": "admin"
            },
            {
                "id": 2,
                "title": "🔧 Команды /teh и /unteh",
                "content": "Режим техобслуживания для сайта. При включении сайт показывает ⚪",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "author": "admin"
            }
        ]
        with open(POSTS_FILE, "w") as f:
            json.dump(default_posts, f, indent=4)
    
    if not os.path.exists(BANNED_FILE):
        with open(BANNED_FILE, "w") as f:
            json.dump([], f, indent=4)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f, indent=4)

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

def load_posts():
    with open(POSTS_FILE, "r") as f:
        return json.load(f)

def save_posts(posts):
    with open(POSTS_FILE, "w") as f:
        json.dump(posts, f, indent=4)

def load_banned():
    with open(BANNED_FILE, "r") as f:
        return json.load(f)

def save_banned(banned_list):
    with open(BANNED_FILE, "w") as f:
        json.dump(banned_list, f, indent=4)

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def is_banned(name):
    banned = load_banned()
    return name in banned

def ban_user(name):
    banned = load_banned()
    if name not in banned:
        banned.append(name)
        save_banned(banned)
        return True
    return False

def unban_user(name):
    banned = load_banned()
    if name in banned:
        banned.remove(name)
        save_banned(banned)
        return True
    return False

def register_user_server(nickname, password_hash):
    users = load_users()
    if nickname in users:
        return False
    users[nickname] = {
        "password_hash": password_hash,
        "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": None
    }
    save_users(users)
    return True

def update_last_login(nickname):
    users = load_users()
    if nickname in users:
        users[nickname]["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        save_users(users)

def verify_password_server(nickname, password_hash):
    users = load_users()
    if nickname not in users:
        return False
    return users[nickname]["password_hash"] == password_hash

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

@app.route("/api/posts", methods=["GET"])
def get_posts():
    return jsonify(load_posts())

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

# ========== РЕГИСТРАЦИЯ ЧЕРЕЗ API ==========
@app.route("/api/register", methods=["POST"])
def api_register():
    req = request.json
    nickname = req.get("nickname", "").strip()
    password_hash = req.get("password_hash", "").strip()
    
    if not nickname or not password_hash:
        return jsonify({"success": False, "error": "Никнейм и пароль обязательны"}), 400
    
    if register_user_server(nickname, password_hash):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Пользователь уже существует"}), 409

@app.route("/api/login", methods=["POST"])
def api_login():
    req = request.json
    nickname = req.get("nickname", "").strip()
    password_hash = req.get("password_hash", "").strip()
    
    if verify_password_server(nickname, password_hash):
        update_last_login(nickname)
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Неверный ник или пароль"}), 401

# ========== ЧАТ ПОДДЕРЖКИ С ЗАЩИТОЙ ОТ СПАМА ==========
@app.route("/api/support/send", methods=["POST"])
def send_support():
    req = request.json
    name = req.get("name", "Аноним")
    message = req.get("message", "").strip()
    
    if is_banned(name):
        return jsonify({"error": "Вы забанены и не можете писать в поддержку"}), 403
    
    if not message:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400
    
    # Защита от спама
    last_message_time = getattr(send_support, "last_message_time", {})
    if name in last_message_time:
        time_since_last = time.time() - last_message_time[name]
        if time_since_last < 30:
            return jsonify({"error": "Слишком часто. Подождите 30 секунд."}), 429
    
    last_message_content = getattr(send_support, "last_message_content", {})
    if last_message_content.get(name) == message:
        return jsonify({"error": "Не спамьте одинаковыми сообщениями"}), 429
    
    spam_keywords = ["робуксы", "робукс", "robux", "вайбкодер", "vibe", "ажахелужцэыдады", "фуу", "дичь", "спам", "халява", "бесплатно", "admin", "hack", "взлом", "дайте", "пж", "пжпж"]
    for keyword in spam_keywords:
        if keyword.lower() in message.lower():
            ban_user(name)
            return jsonify({"error": "Вы забанены за спам"}), 403
    
    last_message_time[name] = time.time()
    last_message_content[name] = message
    send_support.last_message_time = last_message_time
    send_support.last_message_content = last_message_content
    
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

# ========== АДМИН-ПАНЕЛЬ (С ПАРОЛЕМ) ==========
@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.cookies.get("admin_auth") == ADMIN_PASSWORD_HASH:
        return render_admin_panel()
    
    if request.method == "POST":
        password = request.form.get("password", "")
        if simple_hash(password) == ADMIN_PASSWORD_HASH:
            resp = make_response(render_admin_panel())
            resp.set_cookie("admin_auth", ADMIN_PASSWORD_HASH, max_age=3600, httponly=True, samesite='Lax')
            return resp
        else:
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>Доступ запрещён</title><style>body{background:#0a0a0a;color:#eee;font-family:monospace;padding:20px;}</style></head>
            <body>
            <h2>🔐 Неверный пароль</h2>
            <a href="/admin">← Попробовать снова</a>
            </body>
            </html>
            ''', 403
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Вход в админ-панель</title>
    <style>
        body{background:#0a0a0a;color:#eee;font-family:monospace;padding:20px;text-align:center;}
        input{background:#1a1a1a;border:1px solid #ff6b5c;color:white;padding:12px 20px;border-radius:60px;width:300px;margin-bottom:15px;}
        button{background:#ff6b5c;border:none;padding:10px 25px;border-radius:60px;cursor:pointer;font-weight:bold;}
        .container{background:#111;border:1px solid #2c2c2c;border-radius:32px;padding:30px;max-width:450px;margin:50px auto;}
    </style>
    </head>
    <body>
    <div class="container">
        <h2>🔐 Вход в админ-панель</h2>
        <form method="post">
            <input type="password" name="password" placeholder="Введите пароль">
            <br>
            <button type="submit">Войти</button>
        </form>
    </div>
    </body>
    </html>
    '''

def render_admin_panel():
    maintenance = get_maintenance_mode()
    support_list = load_support()
    unanswered = [r for r in support_list if r["status"] == "new"]
    answered = [r for r in support_list if r["status"] == "answered"]
    posts = load_posts()
    banned_users = load_banned()
    users = load_users()
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Alpa Server Admin</title>
        <style>
            body{background:#0a0a0a;color:#eee;font-family:monospace;padding:20px;}
            h1,h2,h3{color:#ff6b5c;}
            .section{background:#111;border:1px solid #2c2c2c;border-radius:16px;padding:15px;margin-bottom:20px;}
            input,textarea{background:#1a1a1a;border:1px solid #333;color:white;padding:8px;width:100%;margin-bottom:10px;border-radius:8px;}
            button{background:#ff6b5c;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-weight:bold;}
            .request{background:#1a1a1a;border-left:3px solid #ff6b5c;padding:10px;margin-bottom:10px;}
            .answered{opacity:0.7;border-left-color:#6bff6b;}
            .post-item{background:#1a1a1a;padding:10px;margin-bottom:10px;border-radius:8px;}
            hr{border-color:#2c2c2c;}
            table{width:100%;border-collapse:collapse;}
            th,td{text-align:left;padding:8px;border-bottom:1px solid #2c2c2c;}
        </style>
    </head>
    <body>
        <h1>🔧 Админ-панель</h1>
        
        <div class="section">
            <h2>🛠 Режим техобслуживания</h2>
            <p>Текущий статус: <strong>{% if maintenance %}⚠️ ВКЛЮЧЁН{% else %}✅ ВЫКЛЮЧЁН{% endif %}</strong></p>
            <form method="post" style="display:inline-block;">
                <input type="hidden" name="action" value="teh">
                <button type="submit">🔧 Включить /teh</button>
            </form>
            <form method="post" style="display:inline-block;margin-left:10px;">
                <input type="hidden" name="action" value="unteh">
                <button type="submit" style="background:#6bff6b;color:#0a0a0a;">✅ Выключить /unteh</button>
            </form>
        </div>
        
        <div class="section">
            <h2>👥 Зарегистрированные пользователи ({{ users|length }})</h2>
            <table>
                <tr><th>Никнейм</th><th>Дата регистрации</th><th>Последний вход</th><th>Действие</th></tr>
                {% for name, data in users.items() %}
                <tr>
                    <td>{{ name }}</td>
                    <td>{{ data.registered_at }}</td>
                    <td>{{ data.last_login or 'никогда' }}</td>
                    <td>
                        <form method="post" style="display:inline;">
                            <input type="hidden" name="action" value="delete_user">
                            <input type="hidden" name="delete_user_name" value="{{ name }}">
                            <button type="submit" style="background:#ff4444;padding:4px 12px;">🗑 Удалить</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
            {% if users|length == 0 %}
            <p>📭 Нет зарегистрированных пользователей</p>
            {% endif %}
        </div>
        
        <div class="section">
            <h2>🔨 Управление банами</h2>
            <p>Забаненные: {{ banned_users|join(", ") if banned_users else "нет" }}</p>
            <form method="post" style="display:inline-block;">
                <input type="hidden" name="action" value="ban">
                <input type="text" name="ban_name" placeholder="Ник для бана" style="width:200px;">
                <button type="submit">🔨 /ban</button>
            </form>
            <form method="post" style="display:inline-block;margin-left:10px;">
                <input type="hidden" name="action" value="unban">
                <input type="text" name="unban_name" placeholder="Ник для разбана" style="width:200px;">
                <button type="submit" style="background:#6bff6b;color:#0a0a0a;">✅ /unban</button>
            </form>
        </div>
        
        <div class="section">
            <h2>📝 Управление постами</h2>
            <h3>Создать новый пост</h3>
            <form method="post">
                <input type="hidden" name="action" value="create_post">
                <input type="text" name="post_title" placeholder="Заголовок">
                <textarea name="post_content" placeholder="Содержание поста..." rows="3"></textarea>
                <button type="submit">➕ Создать пост</button>
            </form>
            <h3>Существующие посты</h3>
            {% for post in posts %}
            <div class="post-item">
                <strong>#{{ post.id }} | {{ post.title }}</strong><br>
                <small>{{ post.date }}</small>
                <p>{{ post.content[:100] }}...</p>
                <form method="post" style="display:inline-block;">
                    <input type="hidden" name="action" value="delete_post">
                    <input type="hidden" name="post_id" value="{{ post.id }}">
                    <button type="submit" style="background:#ff4444;">🗑 Удалить</button>
                </form>
                <button onclick="showEditForm({{ post.id }}, '{{ post.title|replace("'", "\\'") }}', `{{ post.content|replace("`", "\\`") }}`)">✏️ Редактировать</button>
            </div>
            {% endfor %}
            <div id="editForm" style="display:none; margin-top:15px;">
                <h3>Редактировать пост</h3>
                <form method="post">
                    <input type="hidden" name="action" value="edit_post">
                    <input type="hidden" name="edit_id" id="edit_id">
                    <input type="text" name="edit_title" id="edit_title" placeholder="Заголовок">
                    <textarea name="edit_content" id="edit_content" placeholder="Содержание" rows="3"></textarea>
                    <button type="submit">💾 Сохранить изменения</button>
                </form>
            </div>
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
        
        <script>
            function showEditForm(id, title, content) {
                document.getElementById('editForm').style.display = 'block';
                document.getElementById('edit_id').value = id;
                document.getElementById('edit_title').value = title;
                document.getElementById('edit_content').value = content;
            }
        </script>
    </body>
    </html>
    ''', maintenance=maintenance, unanswered=unanswered, answered=answered, posts=posts, banned_users=banned_users, users=users)

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
    print(f"📡 API: /api/top, /api/posts, /api/register, /api/login")
    print(f"🔧 Админ-панель: /admin (пароль: S2a9jlq69J4b2FZ20xoL9eVhw1Qm)")
    app.run(host="0.0.0.0", port=PORT, debug=False)
