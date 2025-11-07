from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from extensions import mongo

auth_bp = Blueprint('auth', __name__)

def validate_auth_data(data):
    errors = {}
    username = data.get('username', '')
    password = data.get('password', '')

    if not isinstance(username, str) or not (3 <= len(username) <= 30):
        errors['username'] = 'O nome de usuário deve ter entre 3 e 30 caracteres.'
    if not isinstance(password, str) or not (5 <= len(password) <= 32):
        errors['password'] = 'A senha deve ter entre 5 e 32 caracteres.'

    return errors


@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra um novo usuário com validação manual"""
    data = request.get_json() or {}

    errors = validate_auth_data(data)
    if errors:
        return jsonify({'msg': 'Erro de validação', 'errors': errors}), 400

    users = mongo.db.users

    # Verifica se já existe o usuário
    if users.find_one({'username': data['username']}):
        return jsonify({'msg': 'usuario_existente'}), 409

    password_hash = generate_password_hash(data['password'])
    users.insert_one({
        'username': data['username'],
        'password': password_hash
    })

    return jsonify({'msg': 'criado'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica usuário com validação manual"""
    data = request.get_json() or {}

    errors = validate_auth_data(data)
    if errors:
        return jsonify({'msg': 'Erro de validação', 'errors': errors}), 400

    users = mongo.db.users
    user = users.find_one({'username': data['username']})

    if not user or not check_password_hash(user['password'], data['password']):
        return jsonify({'msg': 'credenciais_invalidas'}), 401

    access = create_access_token(identity=str(user['_id']))
    return jsonify({
        'access_token': access,
        'username': user['username']
    }), 200
