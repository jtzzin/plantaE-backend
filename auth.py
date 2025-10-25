# backend/auth.py
# Rotas de registro e login de usuários

from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from extensions import mongo  # Importa de extensions agora

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra um novo usuário"""
    data = request.get_json()
    if not data:
        return jsonify({'msg': 'Sem dados'}), 400

    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'msg': 'username e password são obrigatórios'}), 400

    users = mongo.db.users
    
    # Verifica se já existe usuário
    if users.find_one({'username': username}):
        return jsonify({'msg': 'usuario_existente'}), 409

    # Cria usuário
    password_hash = generate_password_hash(password)
    users.insert_one({
        'username': username,
        'password': password_hash
    })
    
    return jsonify({'msg': 'criado'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica usuário"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    users = mongo.db.users
    user = users.find_one({'username': username})
    
    if not user or not check_password_hash(user['password'], password):
        return jsonify({'msg': 'credenciais_invalidas'}), 401

    access = create_access_token(identity=str(user['_id']))
    return jsonify({
        'access_token': access,
        'username': user['username']
    }), 200
