import os
import time
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) # CORS mais permissivo para debug

# Configuration
UPLOAD_FOLDER = 'uploads'
PENDING_FOLDER = 'pending'
STATUS_FOLDER = 'status'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'txt'}

def ensure_directories():
    """Garante que as pastas essenciais existam."""
    for folder in [UPLOAD_FOLDER, PENDING_FOLDER, STATUS_FOLDER]:
        if not os.path.exists(folder):
            os.makedirs(folder)
            logger.info(f"Diretório criado: {folder}")

ensure_directories()

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_request
def log_request_info():
    logger.info(f"Request: {request.method} {request.url}")

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "Server is running", "time": time.time()})

@app.route('/upload', methods=['POST', 'OPTIONS'])
@app.route('/upload/', methods=['POST', 'OPTIONS'])
def upload_file():
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    logger.info(f"Received upload request. Files: {request.files}")
    if 'file' not in request.files:
        logger.error("No file part in request")
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        logger.error("No filename in request")
        return jsonify({"error": "No selected file"}), 400
    
    filename = secure_filename(f"{int(time.time())}_{file.filename}")
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)
    
    # Mark as pending for the Mac
    with open(os.path.join(PENDING_FOLDER, filename), 'w') as f:
        f.write('pending')
    
    # Initial status
    set_status(filename, "Conteúdo telepaticamente enviado")
    logger.info(f"File {filename} uploaded and marked as pending")
    
    return jsonify({"filename": filename, "status": "Uploaded"}), 200

@app.route('/pending', methods=['GET'])
@app.route('/pending/', methods=['GET'])
def list_pending():
    files = os.listdir(PENDING_FOLDER)
    logger.info(f"Listing pending files: {files}")
    return jsonify(files)

@app.route('/download/<filename>', methods=['GET'])
@app.route('/download/<filename>/', methods=['GET'])
def download_file(filename):
    logger.info(f"Downloading file: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/status/<filename>', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/status/<filename>/', methods=['GET', 'POST', 'OPTIONS'])
def handle_status(filename):
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    if request.method == 'POST':
        data = request.json
        status = data.get('status', 'unknown')
        set_status(filename, status)
        logger.info(f"Status update for {filename}: {status}")
        return jsonify({"success": True})
    else:
        status = get_status(filename)
        return jsonify({"status": status})

@app.route('/processed/<filename>', methods=['DELETE', 'OPTIONS'])
@app.route('/processed/<filename>/', methods=['DELETE', 'OPTIONS'])
def mark_processed(filename):
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"}), 200
        
    logger.info(f"Marking as processed: {filename}")
    
    # 1. Delete from pending folder
    pending_path = os.path.join(PENDING_FOLDER, filename)
    if os.path.exists(pending_path):
        os.remove(pending_path)
    
    # 2. Delete from upload folder (The actual file)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(upload_path):
        os.remove(upload_path)
        logger.info(f"File {filename} deleted from uploads.")
        
    return jsonify({"success": True})

def set_status(filename, status):
    status_path = os.path.join(STATUS_FOLDER, f"{filename}.status")
    with open(status_path, 'w') as f:
        f.write(status)

def get_status(filename):
    status_path = os.path.join(STATUS_FOLDER, f"{filename}.status")
    if os.path.exists(status_path):
        with open(status_path, 'r') as f:
            return f.read()
    return "Aguardando..."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
