from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from flask_pymongo import PyMongo
from flask_cors import CORS
from datetime import datetime
import random
import string

app = Flask(__name__)
CORS(app)

# ==== MongoDB Atlas Configuration ====
app.config["MONGO_URI"] = "mongodb+srv://ojediranifeoluwa2:<db_password>@cluster0.7c45aoe.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo = PyMongo(app)

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

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
    message_text = data['message']

    # Save to MongoDB
    mongo.db.messages.insert_one({
        "sender_id": sender['id'],
        "sender_username": sender['username'],
        "recipient_id": recipient_id,
        "recipient_username": get_username_by_id(recipient_id),
        "message": message_text,
        "is_read": False,
        "timestamp": datetime.utcnow()
    })

    for sid, info in users.items():
        if info['id'] == recipient_id:
            emit('receive_message', {
                'from': sender['username'],
                'from_id': sender['id'],
                'message': message_text,
                'is_read': False
            }, room=sid)
            break


@socketio.on('load_history')
def load_history(data):
    user1_id = users[request.sid]['id']
    user2_id = data['with']

    # Mark unread messages as read
    mongo.db.messages.update_many(
        {"sender_id": user2_id, "recipient_id": user1_id, "is_read": False},
        {"$set": {"is_read": True}}
    )

    # Fetch chat history
    messages = mongo.db.messages.find({
        "$or": [
            {"sender_id": user1_id, "recipient_id": user2_id},
            {"sender_id": user2_id, "recipient_id": user1_id}
        ]
    }).sort("timestamp", 1)

    formatted = [
        {
            'from': msg['sender_username'],
            'from_id': msg['sender_id'],
            'message': msg['message'],
            'timestamp': msg['timestamp'].strftime('%H:%M'),
            'is_read': msg['is_read']
        }
        for msg in messages
    ]

    emit('chat_history', formatted)


@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in users:
        users.pop(request.sid)
        emit('user_list', get_user_list(), broadcast=True)


def get_user_list():
    return [{'id': info['id'], 'username': info['username']}
            for info in users.values() if info['username']]


def get_username_by_id(uid):
    for info in users.values():
        if info['id'] == uid:
            return info['username']
    return "Unknown"

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)