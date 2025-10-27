from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from extensions import mongo
from pydantic import BaseModel, ValidationError, constr


auth_bp = Blueprint('auth', __name__)

# Definindo pydantic para validar username e password
class AuthModel(BaseModel):
    username: constr(min_length=3, max_length=30)
    password: constr(min_length=5, max_length=32)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra um novo usuário com validação"""
    try:
        data = AuthModel(**request.get_json())  # faz validação automática aqui
    except ValidationError as e:
        return jsonify({'msg': 'Erro de validação', 'errors': e.errors()}), 400

    users = mongo.db.users

    # Verifica se já existe o usuário
    if users.find_one({'username': data.username}):
        return jsonify({'msg': 'usuario_existente'}), 409

    password_hash = generate_password_hash(data.password)
    users.insert_one({
        'username': data.username,
        'password': password_hash
    })

    return jsonify({'msg': 'criado'}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """Autentica usuário com validação"""
    try:
        data = AuthModel(**request.get_json())
    except ValidationError as e:
        return jsonify({'msg': 'Erro de validação', 'errors': e.errors()}), 400

    users = mongo.db.users
    user = users.find_one({'username': data.username})

    if not user or not check_password_hash(user['password'], data.password):
        return jsonify({'msg': 'credenciais_invalidas'}), 401

    access = create_access_token(identity=str(user['_id']))
    return jsonify({
        'access_token': access,
        'username': user['username']
    }), 200
