# backend/plants.py
# Rotas para CRUD de plantas

from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from bson import ObjectId
from extensions import mongo  # Importa de extensions agora

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

plants_bp = Blueprint('plants', __name__)

def allowed_file(filename):
    """Verifica extensão permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

@plants_bp.route('/test', methods=['GET'])
def test():
    """Teste da API"""
    return jsonify({'ok': True})

@plants_bp.route('/', methods=['GET'])
@jwt_required()
def list_plants():
    """Lista plantas do usuário"""
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    docs = list(coll.find({'owner': user_id}))
    
    for d in docs:
        d['_id'] = str(d['_id'])
    
    return jsonify(docs)

@plants_bp.route('/', methods=['POST'])
@jwt_required()
def create_plant():
    """Cria nova planta"""
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
    """Retorna planta por ID"""
    coll = mongo.db.plants
    p = coll.find_one({'_id': ObjectId(plant_id)})
    
    if not p:
        return jsonify({}), 404
    
    p['_id'] = str(p['_id'])
    return jsonify(p)

@plants_bp.route('/<plant_id>', methods=['DELETE'])
@jwt_required()
def delete_plant(plant_id):
    """Exclui planta"""
    coll = mongo.db.plants
    res = coll.delete_one({'_id': ObjectId(plant_id)})
    return jsonify({'deleted': res.deleted_count}), 200

@plants_bp.route('/<plant_id>/water', methods=['POST'])
@jwt_required()
def water_plant(plant_id):
    """Registra rega"""
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    
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
    """Upload de foto"""
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

@plants_bp.route('/photo/<filename>', methods=['GET'])
def serve_photo(filename):
    """Serve foto"""
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)
