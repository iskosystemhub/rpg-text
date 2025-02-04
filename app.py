import os
import sqlite3
from flask import Flask, render_template, session, redirect, url_for, request, jsonify
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.secret_key = 'secret_key'
socketio = SocketIO(app)

# Hardcoded DM credentials for this example
dm_credentials = {
    "admin": "password123",
    "gm": "game123",
}

# Predefined list of NPCs (in memory)
npc_names = ["Big Burly Man", "Wife", "Shopkeeper", "Guard", "Barkeep"]

# --- Database Setup ---
DATABASE = 'chat.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_message(sender, message):
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('INSERT INTO messages (sender, message) VALUES (?, ?)', (sender, message))
    conn.commit()
    conn.close()

def get_all_messages():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('SELECT sender, message, timestamp FROM messages ORDER BY id')
    rows = c.fetchall()
    conn.close()
    messages = []
    for row in rows:
        messages.append({'sender': row[0], 'message': row[1], 'timestamp': row[2]})
    return messages

init_db()
# --- End Database Setup ---

@app.route('/')
def index():
    if 'role' in session:
        if session['role'] == 'player':
            return redirect(url_for('player_screen'))
        elif session['role'] == 'dm':
            return redirect(url_for('dm_screen'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')  # May be empty if player login

    # DM login if password provided
    if password:
        if username in dm_credentials and dm_credentials[username] == password:
            session['role'] = 'dm'
            session['dm_name'] = username
            return redirect(url_for('dm_screen'))
        else:
            return redirect(url_for('index'))
    else:
        # Player login
        if username:
            session['role'] = 'player'
            session['player_name'] = username
            return redirect(url_for('player_screen'))
        else:
            return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/player_screen')
def player_screen():
    if 'role' not in session or session['role'] != 'player':
        return redirect(url_for('index'))
    return render_template('player_screen.html', player_name=session['player_name'])

@app.route('/dm_screen')
def dm_screen():
    if 'role' not in session or session['role'] != 'dm':
        return redirect(url_for('index'))
    return render_template('dm_screen.html', dm_name=session['dm_name'], npc_names=npc_names)

@app.route('/add_npc', methods=['POST'])
def add_npc():
    if 'role' not in session or session['role'] != 'dm':
        return redirect(url_for('index'))
    npc_name = request.form.get('npc_name')
    if npc_name:
        npc_names.append(npc_name)
    return redirect(url_for('dm_screen'))

@app.route('/messages')
def messages():
    return jsonify(get_all_messages())

@socketio.on('message')
def handle_message(msg):
    """
    For players, the message will be prefixed with their name on the client side.
    For DM, we assume the message already includes the speaker (chosen from the dropdown).
    """
    if 'role' in session:
        if session['role'] == 'player':
            sender = session.get('player_name', 'Player')
            full_msg = f"{sender}: {msg}"
        elif session['role'] == 'dm':
            # For DM, the msg already has the format "Speaker: message"
            full_msg = msg
            # Optionally, extract the sender name from the message:
            sender = msg.split(":")[0]
    else:
        full_msg = msg
        sender = "Anonymous"

    # Save the message and broadcast it
    save_message(sender, full_msg)
    send(full_msg, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, debug=True)

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)

