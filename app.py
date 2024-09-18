from flask import Flask, request, jsonify, send_from_directory, g
import pyttsx3
import os
import uuid
import sqlite3

app = Flask(__name__)

# Inicializa o mecanismo de texto para fala
engine = pyttsx3.init()
# Obtém a lista de vozes disponíveis
voices = engine.getProperty('voices')
# Define a taxa de fala (palavras por minuto)
engine.setProperty('rate', 150)

# Configuração do banco de dados SQLite
DATABASE = 'tokens.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
    return g.db

def init_db():
    db = get_db()
    db.execute('CREATE TABLE IF NOT EXISTS tokens (token TEXT PRIMARY KEY)')
    db.commit()

@app.route('/generate-token', methods=['POST'])
def generate_token():
    token = str(uuid.uuid4())
    db = get_db()
    db.execute('INSERT INTO tokens (token) VALUES (?)', (token,))
    db.commit()
    return jsonify({'token': token}), 201

def validate_token(token):
    db = get_db()
    result = db.execute('SELECT * FROM tokens WHERE token = ?', (token,)).fetchone()
    return result is not None

def token_required(f):
    def decorator(*args, **kwargs):
        return f(*args, **kwargs)  # Não faz mais a verificação aqui, vamos fazer no endpoint
    decorator.__name__ = f.__name__  # Adiciona o nome da função original ao decorador
    return decorator

@app.route('/text-to-speech', methods=['POST'])
@token_required
def text_to_speech():
    data = request.json
    # Verifica se o texto e o token foram fornecidos
    if 'text' not in data or 'token' not in data:
        return jsonify({'error': 'Texto ou token não fornecido'}), 400
    
    text = data['text']
    token = data['token']  # Captura o token do corpo da requisição

    # Valida o token
    if not validate_token(token):
        return jsonify({'error': 'Token inválido'}), 403
    
    voice_id = data.get('voice', None)  # Opcional: ID da voz
    
    audio_file = f"{uuid.uuid4()}.mp3"
    
    if voice_id is not None:
        if int(voice_id) < len(voices):
            engine.setProperty('voice', voices[int(voice_id)].id)
        else:
            return jsonify({'error': 'ID da voz inválido'}), 400
            
    engine.save_to_file(text, audio_file)
    engine.runAndWait()
    
    download_link = f"https://voice.altekweb.com.br/download/{audio_file}"
    
    return jsonify({'download_link': download_link}), 200

@app.route('/download/<filename>', methods=['GET'])
@token_required
def download(filename):
    current_directory = os.getcwd()
    return send_from_directory(current_directory, filename, as_attachment=True)

@app.route('/voices', methods=['GET'])
@token_required
def list_voices():
    voice_list = [{"id": index, "name": voice.name} for index, voice in enumerate(voices)]
    return jsonify(voice_list), 200

@app.teardown_appcontext
def close_connection(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

if __name__ == '__main__':
    with app.app_context():
        init_db()  # Inicializa o banco de dados dentro do contexto da aplicação
    app.run(debug=True, port=5125)
