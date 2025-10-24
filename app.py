# backend/app.py
# Aplicação Flask principal do PlantaE, configuração do MongoDB e JWT.
# Comentários em português explicando cada parte.

from flask import Flask
from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv()

app = Flask(__name__)

# Configurações (leia e preencha .env antes de rodar)
# A URI do Mongo deve ser colocada em .env baseado no .env.example fornecido.
app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
# Chave secreta para assinar tokens JWT; configure no .env
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'dev-secret'
# Pasta onde as imagens serão salvas; configure no .env
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

# Inicializa conexão com MongoDB e JWT
mongo = PyMongo(app)
jwt = JWTManager(app)

# Importa blueprints (rotas organizadas)
from auth import auth_bp
from plants import plants_bp

# Registra blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(plants_bp, url_prefix='/api/plants')

if __name__ == '__main__':
    # Garante que a pasta de uploads exista
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    # Executa em modo de desenvolvimento (para produção, ajuste conforme necessário)
    app.run(debug=True, port=5000)
