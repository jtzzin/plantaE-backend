# backend/plants.py
# Rotas para CRUD de plantas, histórico de regas e upload de foto.
# Comentários em português em cada endpoint.

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
from app import mongo

ALLOWED_EXT = {'png','jpg','jpeg','gif'}

plants_bp = Blueprint('plants', __name__)

def allowed_file(filename):
    """Verifica se a extensão do arquivo está na lista permitida."""
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXT

@plants_bp.route('/test', methods=['GET'])
def test():
    """Rota simples para checar se a API está no ar."""
    return jsonify({'ok': True})

@plants_bp.route('/', methods=['GET'])
@jwt_required()
def list_plants():
    """Lista todas as plantas do usuário autenticado."""
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    docs = list(coll.find({'owner': user_id}))
    # Converte ObjectId para string para permitir JSON
    for d in docs:
        d['_id'] = str(d['_id'])
    return jsonify(docs)

@plants_bp.route('/', methods=['POST'])
@jwt_required()
def create_plant():
    """Cria uma nova planta.
    Aceita form-data (para foto) ou JSON com campos:
    - name: nome da planta
    - water_interval_days: intervalo de rega em dias (int)
    - notes: observações (opcional)
    """
    user_id = get_jwt_identity()
    # Lê form-data (quando houver arquivo) ou JSON
    data = request.form.to_dict() or request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({'msg':'nome_obrigatorio'}), 400
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
        'created_at': datetime.utcnow(),
        'last_watered': None,
        'water_history': [],
        'photo': None
    }
    res = coll.insert_one(plant)
    return jsonify({'_id': str(res.inserted_id)}), 201

@plants_bp.route('/<plant_id>', methods=['GET'])
@jwt_required()
def get_plant(plant_id):
    """Retorna dados de uma planta específica pelo ID."""
    coll = mongo.db.plants
    from bson import ObjectId
    p = coll.find_one({'_id': ObjectId(plant_id)})
    if not p:
        return jsonify({}), 404
    p['_id'] = str(p['_id'])
    return jsonify(p)

@plants_bp.route('/<plant_id>', methods=['DELETE'])
@jwt_required()
def delete_plant(plant_id):
    """Exclui a planta especificada por ID."""
    coll = mongo.db.plants
    from bson import ObjectId
    res = coll.delete_one({'_id': ObjectId(plant_id)})
    return jsonify({'deleted': res.deleted_count}), 200

@plants_bp.route('/<plant_id>/water', methods=['POST'])
@jwt_required()
def water_plant(plant_id):
    """Registra uma rega manual: adiciona item ao histórico e atualiza last_watered."""
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    from bson import ObjectId
    time = datetime.utcnow()
    update = {
        '$push': {'water_history': {'at': time, 'by': user_id}},
        '$set': {'last_watered': time}
    }
    coll.update_one({'_id': ObjectId(plant_id)}, update)
    return jsonify({'ok': True}), 200

@plants_bp.route('/<plant_id>/upload', methods=['POST'])
@jwt_required()
def upload_photo(plant_id):
    """Recebe arquivo via form-data com campo 'photo' e salva no servidor.
    - Retorna o nome do arquivo salvo.
    - Lembre-se: para produção, prefira S3 / armazenamento em nuvem ou GridFS.
    """
    if 'photo' not in request.files:
        return jsonify({'msg':'arquivo_nao_enviado'}), 400
    file = request.files['photo']
    if file.filename == '':
        return jsonify({'msg':'nome_vazio'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_to = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        # Salva arquivo na pasta configurada
        file.save(save_to)
        coll = mongo.db.plants
        from bson import ObjectId
        coll.update_one({'_id': ObjectId(plant_id)}, {'$set': {'photo': filename}})
        return jsonify({'filename': filename}), 200
    return jsonify({'msg':'arquivo_invalido'}), 400

@plants_bp.route('/photo/<filename>', methods=['GET'])
def serve_photo(filename):
    """Serve as fotos salvas para o frontend exibir."""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
