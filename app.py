# backend/app.py
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()
print('MONGO_URI:', os.environ.get('MONGO_URI'))

app = Flask(__name__)
app.url_map.strict_slashes = False

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)

app.config['MONGO_URI'] = os.environ.get('MONGO_URI')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY') or 'dev-secret'
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', 'uploads')

from extensions import mongo, jwt
mongo.init_app(app)
jwt.init_app(app)

from auth import auth_bp
from plants import plants_bp
from activities import activities_bp

app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(plants_bp, url_prefix='/api/plants')
app.register_blueprint(activities_bp, url_prefix='/api/activities')

@app.route('/')
def index():
    return {'message': 'API PlantaE rodando...'}, 200

@app.route('/ping')
def ping():
    print('recebeu ping')
    return {'message': 'pong'}, 200

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    try:
        mongo.db.command('ping')
        print('Conectado ao MongoDB')
    except Exception as e:
        print(f'Erro ao conectar ao MongoDB: {e}')
        exit(1)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port, host='0.0.0.0')
