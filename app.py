# backend/app.py
# Aplicação Flask principal do PlantaE

from flask import Flask
from flask_cors import CORS  # ← IMPORTA CORS
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()
print('MONGO_URI:', os.environ.get('MONGO_URI'))


app = Flask(__name__)
CORS(app)  # ← HABILITA CORS (permite frontend acessar)

# Configurações
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'dev-secret'
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

# Importa extensões
from extensions import mongo, jwt

# Inicializa extensões com o app
mongo.init_app(app)
jwt.init_app(app)

# Importa blueprints (DEPOIS de inicializar as extensões)
from auth import auth_bp
from plants import plants_bp

# Registra blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(plants_bp, url_prefix='/api/plants')

@app.route('/')
def index():
    """Rota raiz"""
    return {'message': 'API PlantaE rodando...'}, 200

@app.route('/ping')
def ping():
    """Health check"""
    print('recebeu ping')
    return {'message': 'pong'}, 200

if __name__ == '__main__':
    # Garante que a pasta de uploads exista
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Testa conexão com MongoDB
    try:
        mongo.db.command('ping')
        print('✅ Conectado ao MongoDB')
    except Exception as e:
        print(f'❌ Erro ao conectar ao MongoDB: {e}')
        exit(1)
    
    # Executa servidor
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port, host='0.0.0.0')
