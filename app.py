# backend/app.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from pathlib import Path
import os

# Carrega variáveis do .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Inicializa app Flask
app = Flask(__name__)
app.url_map.strict_slashes = False

# Configurações básicas
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret')
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

# Verifica se URI foi carregada
if app.debug:
    print(f"MONGO_URI carregada? {'Sim' if app.config['MONGO_URI'] else 'Não'}")

# Configura CORS 
CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

# Inicializa extensões
from extensions import mongo, jwt
mongo.init_app(app)
jwt.init_app(app)

# Blueprints
from auth import auth_bp
from plants import plants_bp
from activities import activities_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(plants_bp, url_prefix='/api/plants')
app.register_blueprint(activities_bp, url_prefix='/api/activities')

# Rotas básicas 
@app.route('/')
def index():
    return {'message': 'API PlantaE rodando...'}, 200

@app.route('/ping')
def ping():
    print('Recebeu ping')
    return {'message': 'pong'}, 200

# Execução principal
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    try:
        mongo.db.command('ping')
        print('Conectado ao MongoDB')
    except Exception as e:
        print(f'Erro ao conectar ao MongoDB: {e}')
        exit(1)

    port = int(os.environ.get('PORT', 5000))
    print(f'Servidor rodando em http://localhost:{port}')
    app.run(debug=True, port=port, host='0.0.0.0')
