from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Модель данных
class DataEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    data = db.Column(db.Text)  # Храним JSON как текст
    source_ip = db.Column(db.String(50))
    method = db.Column(db.String(10))

    def to_dict(self):
        return {
            'id': self.id,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'data': json.loads(self.data) if self.data else {},
            'source_ip': self.source_ip,
            'method': self.method
        }

# Создание таблиц
with app.app_context():
    db.create_all()

# Главная страница с отображением данных
@app.route('/')
def index():
    entries = DataEntry.query.order_by(DataEntry.timestamp.desc()).all()
    return render_template('index.html', entries=entries)

# API для приёма данных (вебхук) - ИЗМЕНЕН ТОЛЬКО ЭТОТ ОБРАБОТЧИК
@app.route('/webhook', methods=['POST', 'GET', 'PUT', 'DELETE'])
def webhook():
    # Получаем данные в зависимости от метода
    if request.method == 'GET':
        data = request.args.to_dict()
    else:
        data = request.get_json(silent=True) or request.form.to_dict() or request.args.to_dict()
    
    # ПРЕОБРАЗУЕМ ДАННЫЕ В СПИСОК, ЕСЛИ ЭТО НЕ СПИСОК
    if isinstance(data, dict):
        # Если это словарь, берем только значения и преобразуем в список
        data_list = list(data.values())
    elif isinstance(data, list):
        # Если это уже список, оставляем как есть
        data_list = data
    else:
        # Если что-то другое, делаем список с одним элементом
        data_list = [data]
    
    # Сохраняем в базу
    entry = DataEntry(
        data=json.dumps(data_list, ensure_ascii=False),
        source_ip=request.remote_addr,
        method=request.method
    )
    db.session.add(entry)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': 'Data received',
        'id': entry.id
    }), 200

# API для получения всех данных
@app.route('/api/data')
def get_data():
    entries = DataEntry.query.order_by(DataEntry.timestamp.desc()).all()
    return jsonify([entry.to_dict() for entry in entries])

# API для получения конкретной записи
@app.route('/api/data/<int:entry_id>')
def get_entry(entry_id):
    entry = DataEntry.query.get_or_404(entry_id)
    return jsonify(entry.to_dict())

# Очистка базы (опционально)
@app.route('/clear', methods=['POST'])
def clear_database():
    try:
        db.session.query(DataEntry).delete()
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Database cleared'})
    except:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Error clearing database'}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)