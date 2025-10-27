from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from bson import ObjectId
from extensions import mongo  # extensão do db

# Lista de extensões de imagens permitidas
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

# Cria um "grupo" de rotas para plantas
plants_bp = Blueprint('plants', __name__)

# Função para checar se o arquivo enviado é permitido
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

# TESTE DE API - Só retorna ok pra saber se tá rodando
@plants_bp.route('/test', methods=['GET'])
def test():
    return jsonify({'ok': True})

# Lista todas as plantas do usuário logado
@plants_bp.route('/', methods=['GET'])
@jwt_required()
def list_plants():
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    docs = list(coll.find({'owner': user_id}))
    for d in docs:
        d['_id'] = str(d['_id'])
    return jsonify(docs)

# Cria uma nova planta conforme dados enviados pelo usuário
@plants_bp.route('/', methods=['POST'])
@jwt_required()
def create_plant():
    user_id = get_jwt_identity()
    data = request.form.to_dict() or request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'msg': 'nome_obrigatorio'}), 400

    try:
        water_interval_days = int(data.get('water_interval_days', 7))
    except:
        water_interval_days = 7

    notes = data.get('notes', '')
    coll = mongo.db.plants
    plant = {
        'owner': user_id,
        'name': name,
        'water_interval_days': water_interval_days,
        'notes': notes,
        'created_at': datetime.utcnow(),  # Momento da criação
        'last_watered': None,
        'water_history': [],  # Histórico das regas
        'photo': None
    }

    res = coll.insert_one(plant)
    return jsonify({'_id': str(res.inserted_id)}), 201

# Retorna os dados completos de uma planta pela id
@plants_bp.route('/<plant_id>', methods=['GET'])
@jwt_required()
def get_plant(plant_id):
    coll = mongo.db.plants
    p = coll.find_one({'_id': ObjectId(plant_id)})
    if not p:
        return jsonify({}), 404
    p['_id'] = str(p['_id'])
    return jsonify(p)

# Exclui uma planta do banco usando o id
@plants_bp.route('/<plant_id>', methods=['DELETE'])
@jwt_required()
def delete_plant(plant_id):
    coll = mongo.db.plants
    res = coll.delete_one({'_id': ObjectId(plant_id)})
    return jsonify({'deleted': res.deleted_count}), 200

# ROTINA PRINCIPAL DE REGA
# Sempre que clicar em regar, adiciona data/hora no histórico
@plants_bp.route('/<plant_id>/water', methods=['POST'])
@jwt_required()
def water_plant(plant_id):
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    time = datetime.utcnow()
    update = {
        '$push': {'water_history': {'at': time, 'by': user_id}},  # Adiciona no hist
        '$set': {'last_watered': time}  # Atualiza último horário de rega
    }
    coll.update_one({'_id': ObjectId(plant_id)}, update)
    return jsonify({'ok': True}), 200

# Envia uma foto da planta e salva o nome da imagem
@plants_bp.route('/<plant_id>/upload', methods=['POST'])
@jwt_required()
def upload_photo(plant_id):
    if 'photo' not in request.files:
        return jsonify({'msg': 'arquivo_nao_enviado'}), 400

    file = request.files['photo']
    if file.filename == '':
        return jsonify({'msg': 'nome_vazio'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filename = f"{datetime.utcnow().timestamp()}_{filename}"
        save_to = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(save_to)
        coll = mongo.db.plants
        coll.update_one(
            {'_id': ObjectId(plant_id)},
            {'$set': {'photo': filename}}
        )
        return jsonify({'filename': filename}), 200

    return jsonify({'msg': 'arquivo_invalido'}), 400

# Rota para baixar/mostrar a foto da planta pelo nome do arquivo
@plants_bp.route('/photo/<filename>', methods=['GET'])
def serve_photo(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
