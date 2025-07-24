from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import random
import string
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# ========= DATABASE =========


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.String(6))
    sender_username = db.Column(db.String(100))
    recipient_id = db.Column(db.String(6))
    recipient_username = db.Column(db.String(100))
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)  # ✅ NEW

# ========= USERS =========
users = {}  # sid -> {'username': ..., 'id': ...}

def generate_user_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    user_id = generate_user_id()
    users[request.sid] = {'username': None, 'id': user_id}
    emit('assign_id', user_id)

@socketio.on('set_username')
def set_username(data):
    users[request.sid]['username'] = data
    emit('user_list', get_user_list(), broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    sender = users[request.sid]
    recipient_id = data['to']
    message = data['message']

    for sid, info in users.items():
        if info['id'] == recipient_id:
            msg = Message(
                sender_id=sender['id'],
                sender_username=sender['username'],
                recipient_id=info['id'],
                recipient_username=info['username'],
                message=message,
                is_read=False
            )
            db.session.add(msg)
            db.session.commit()

            emit('receive_message', {
                'from': sender['username'],
                'from_id': sender['id'],
                'message': message,
                'is_read': False
            }, room=sid)
            break

@socketio.on('load_history')
def load_history(data):
    user1_id = users[request.sid]['id']
    user2_id = data['with']

    unread_msgs = Message.query.filter_by(
        sender_id=user2_id,
        recipient_id=user1_id,
        is_read=False
    ).all()

    for msg in unread_msgs:
        msg.is_read = True
    db.session.commit()

    history = Message.query.filter(
        ((Message.sender_id == user1_id) & (Message.recipient_id == user2_id)) |
        ((Message.sender_id == user2_id) & (Message.recipient_id == user1_id))
    ).order_by(Message.timestamp).all()

    formatted = [
        {
            'from': msg.sender_username,
            'from_id': msg.sender_id,
            'message': msg.message,
            'timestamp': msg.timestamp.strftime('%H:%M'),
            'is_read': msg.is_read
        }
        for msg in history
    ]

    emit('chat_history', formatted)
    
@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        users.pop(request.sid)
        emit('user_list', get_user_list(), broadcast=True)

def get_user_list():
    return [
        {'id': info['id'], 'username': info['username']}
        for info in users.values() if info['username']
    ]

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, host='0.0.0.0', port=5000)

