import json
import os
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")  # разрешаем всем

DATA_FILE = "players_data.json"
PORT = 20003
HOST = "0.0.0.0"

# ========== ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ФАЙЛА ==========
if not os.path.exists(DATA_FILE):
    default_data = {
        "players": {
            "Alpa": {"kills": 0, "wins": 0, "defeats": 0, "deaths": 0, "xp": 0}
        },
        "top_positions": {str(i): None for i in range(1, 11)}
    }
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(default_data, f, indent=4, ensure_ascii=False)
    print(f"✅ Создан новый файл {DATA_FILE}")
else:
    print(f"✅ Файл {DATA_FILE} уже существует")

# ========== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ==========
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Ошибка чтения: {e}. Создаём заново.")
        default_data = {
            "players": {
                "Alpa": {"kills": 0, "wins": 0, "defeats": 0, "deaths": 0, "xp": 0}
            },
            "top_positions": {str(i): None for i in range(1, 11)}
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4, ensure_ascii=False)
        return default_data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ========== API ==========
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

@app.route("/api/command", methods=["POST"])
def run_command():
    req = request.json
    cmd_line = req.get("command", "").strip()
    if not cmd_line:
        return jsonify({"result": "Пустая команда"})
    
    parts = cmd_line.split()
    cmd = parts[0].lower()
    data = load_data()
    
    if cmd == "/set" and len(parts) >= 4:
        name = parts[1]
        stat = parts[2].lower()
        try:
            value = int(parts[3])
        except:
            return jsonify({"result": "❌ Значение должно быть числом"})
        
        if stat not in ["kills", "deaths", "xp", "wins", "defeats"]:
            return jsonify({"result": "❌ Статы: kills, deaths, xp, wins, defeats"})
        
        if name not in data["players"]:
            data["players"][name] = {"kills": 0, "wins": 0, "defeats": 0, "deaths": 0, "xp": 0}
        
        data["players"][name][stat] = value
        save_data(data)
        return jsonify({"result": f"✅ {name}: {stat} = {value}"})
    
    elif cmd == "/settop" and len(parts) >= 3:
        place = parts[1]
        name = parts[2]
        if place not in [str(i) for i in range(1, 11)]:
            return jsonify({"result": "❌ Место от 1 до 10"})
        if name not in data["players"]:
            return jsonify({"result": f"❌ Игрок {name} не найден"})
        data["top_positions"][place] = name
        save_data(data)
        return jsonify({"result": f"🏆 {name} закреплён на {place} месте"})
    
    elif cmd == "/tops":
        players = data["players"]
        if not players:
            return jsonify({"result": "📭 Нет игроков"})
        sorted_players = sorted(players.items(), key=lambda x: x[1].get("xp", 0), reverse=True)
        lines = ["🏅 ТОП-10 по опыту:"]
        for i, (name, stat) in enumerate(sorted_players[:10], 1):
            lines.append(f"{i}. {name} — опыт: {stat.get('xp',0)}")
        return jsonify({"result": "\n".join(lines)})
    
    elif cmd == "/untop" and len(parts) >= 2:
        name = parts[1]
        removed = False
        for place, player in data["top_positions"].items():
            if player == name:
                data["top_positions"][place] = None
                removed = True
        if removed:
            save_data(data)
            return jsonify({"result": f"🗑 {name} удалён из топа"})
        return jsonify({"result": f"❌ {name} не найден"})
    
    else:
        return jsonify({"result": "❌ Доступно: /set, /settop, /tops, /untop"})

@app.route("/admin", methods=["GET", "POST"])
def admin_panel():
    if request.method == "POST":
        cmd = request.form.get("command", "").strip()
        if not cmd:
            return "<pre>❌ Пустая команда</pre><br><a href='/admin'>← Назад</a>"
        
        parts = cmd.split()
        data = load_data()
        
        if parts[0] == "/set" and len(parts) >= 4:
            name, stat, val = parts[1], parts[2].lower(), parts[3]
            try:
                val = int(val)
            except:
                return "<pre>❌ Ошибка: значение должно быть числом</pre><br><a href='/admin'>← Назад</a>"
            if name not in data["players"]:
                data["players"][name] = {"kills":0,"wins":0,"defeats":0,"deaths":0,"xp":0}
            data["players"][name][stat] = val
            save_data(data)
            result = f"✅ {name}: {stat} = {val}"
        elif parts[0] == "/settop" and len(parts) >= 3:
            place, name = parts[1], parts[2]
            if name not in data["players"]:
                result = f"❌ Игрок {name} не найден"
            else:
                data["top_positions"][place] = name
                save_data(data)
                result = f"🏆 {name} закреплён на {place} месте"
        elif parts[0] == "/tops":
            players = data["players"]
            if not players:
                result = "📭 Нет игроков"
            else:
                sorted_players = sorted(players.items(), key=lambda x: x[1].get("xp",0), reverse=True)
                lines = ["🏅 ТОП-10 по опыту:"]
                for i, (name, stat) in enumerate(sorted_players[:10], 1):
                    lines.append(f"{i}. {name} — опыт: {stat.get('xp',0)}")
                result = "\n".join(lines)
        elif parts[0] == "/untop" and len(parts) >= 2:
            name = parts[1]
            removed = False
            for place, player in data["top_positions"].items():
                if player == name:
                    data["top_positions"][place] = None
                    removed = True
            if removed:
                save_data(data)
                result = f"🗑 {name} удалён из топа"
            else:
                result = f"❌ {name} не найден"
        else:
            result = "❌ Неизвестная команда"
        
        return f"<pre>{result}</pre><br><a href='/admin'>← Назад</a>"
    
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>Alpa Server Admin</title><style>body{background:#0a0a0a;color:#eee;font-family:monospace;padding:20px;} input{background:#222;color:#fff;border:1px solid #ff6b5c;padding:8px;width:300px;} button{background:#ff6b5c;border:none;padding:8px 16px;cursor:pointer;} pre{background:#111;padding:10px;border-radius:8px;}</style></head>
    <body>
    <h2>🔧 Управление сервером</h2>
    <form method="post">
        <input type="text" name="command" placeholder="/set Alpa kills 10" size="50">
        <button type="submit">Отправить</button>
    </form>
    <h3>📋 Примеры команд:</h3>
    <pre>
/set Fr0st kills 1488
/set Alpa wins 25
/settop 1 Alpa
/tops
/untop Fr0st
    </pre>
    <p>📡 <a href="/api/top" target="_blank">Посмотреть текущий топ (JSON)</a></p>
    </body>
    </html>
    '''

if __name__ == "__main__":
    print(f"🚀 Сервер запущен на http://{HOST}:{PORT}")
    print(f"📡 API: http://{HOST}:{PORT}/api/top")
    print(f"🔧 Панель управления: http://{HOST}:{PORT}/admin")
    app.run(host=HOST, port=PORT, debug=False)