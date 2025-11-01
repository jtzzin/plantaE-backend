from flask import Blueprint, request, jsonify, current_app, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import os
from bson import ObjectId
from extensions import mongo
from activities import log_activity

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}
plants_bp = Blueprint('plants', __name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT

@plants_bp.route('/test', methods=['GET'])
def test():
    return jsonify({'ok': True})

@plants_bp.route('', methods=['GET'])
@plants_bp.route('/', methods=['GET'])
@jwt_required()
def list_plants():
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    docs = list(coll.find({'owner': user_id}))
    for d in docs:
        d['_id'] = str(d['_id'])
    return jsonify(docs)

@plants_bp.route('', methods=['POST'])
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
    except Exception:
        water_interval_days = 7

    notes = data.get('notes', '')

    def parse_iso_to_utc(iso_str):
        try:
            norm = iso_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(norm)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None

    now = datetime.now(timezone.utc)
    first_iso = data.get('firstwateringat') or data.get('first_watering_at')
    first_dt = None
    if first_iso:
        maybe = parse_iso_to_utc(first_iso)
        if maybe and maybe <= now:
            first_dt = maybe
    if first_dt is None:
        first_dt = now

    coll = mongo.db.plants
    plant = {
        'owner': user_id,
        'name': name,
        'water_interval_days': water_interval_days,
        'notes': notes,
        'created_at': now,
        'last_watered': first_dt,
        'water_history': [{'at': first_dt, 'by': user_id}],
        'photo': None
    }

    res = coll.insert_one(plant)
    pid = str(res.inserted_id)
    # LOGAMENTO AJUSTADO: salva horário real da primeira rega no extra
    log_activity(
        user_id,
        'create',
        plant_id=pid,
        plant_name=name,
        extra={'first_watered': first_dt.isoformat()}
    )
    return jsonify({'_id': pid}), 201

@plants_bp.route('/<plant_id>', methods=['GET'])
@jwt_required()
def get_plant(plant_id):
    coll = mongo.db.plants
    p = coll.find_one({'_id': ObjectId(plant_id)})
    if not p:
        return jsonify({}), 404
    p['_id'] = str(p['_id'])
    return jsonify(p)

@plants_bp.route('/<plant_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_plant(plant_id):
    user_id = get_jwt_identity()
    data = request.form.to_dict() or request.get_json() or {}
    coll = mongo.db.plants

    current = coll.find_one({'_id': ObjectId(plant_id)}) or {}
    changes = []
    updates = {}
    photo_changed = False

    if 'name' in data and data['name'].strip():
        new_name = data['name'].strip()
        if new_name != current.get('name'):
            changes.append({'field': 'name', 'from': current.get('name'), 'to': new_name})
            updates['name'] = new_name

    if 'water_interval_days' in data:
        try:
            new_interval = int(data.get('water_interval_days'))
            if new_interval != current.get('water_interval_days'):
                changes.append({'field': 'water_interval_days', 'from': current.get('water_interval_days'), 'to': new_interval})
                updates['water_interval_days'] = new_interval
        except Exception:
            pass

    if 'notes' in data:
        new_notes = data.get('notes', '')
        if new_notes != current.get('notes'):
            changes.append({'field': 'notes', 'from': current.get('notes'), 'to': new_notes})
            updates['notes'] = new_notes

    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filename = f"{datetime.now(timezone.utc).timestamp()}_{filename}"
            save_to = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(save_to)
            updates['photo'] = filename
            photo_changed = True

    if not updates:
        return jsonify({'msg': 'nada_para_atualizar'}), 400

    coll.update_one({'_id': ObjectId(plant_id)}, {'$set': updates})

    try:
        name_for_log = updates.get('name') or current.get('name')
        log_activity(
            user_id,
            'update',
            plant_id=plant_id,
            plant_name=name_for_log,
            extra={'changes': changes, 'photo_changed': photo_changed}
        )
    except Exception:
        pass

    return jsonify({'ok': True, 'updated': list(updates.keys()), 'changes': changes, 'photo_changed': photo_changed}), 200

@plants_bp.route('/<plant_id>', methods=['DELETE'])
@jwt_required()
def delete_plant(plant_id):
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    existing = coll.find_one({'_id': ObjectId(plant_id)})
    name = existing.get('name') if existing else None
    res = coll.delete_one({'_id': ObjectId(plant_id)})
    log_activity(user_id, 'delete', plant_id=plant_id, plant_name=name)
    return jsonify({'deleted': res.deleted_count}), 200

@plants_bp.route('/<plant_id>/water', methods=['POST'])
@jwt_required()
def water_plant(plant_id):
    user_id = get_jwt_identity()
    coll = mongo.db.plants
    time = datetime.now(timezone.utc)
    update = {
        '$push': {'water_history': {'at': time, 'by': user_id}},
        '$set': {'last_watered': time}
    }
    coll.update_one({'_id': ObjectId(plant_id)}, update)
    p = coll.find_one({'_id': ObjectId(plant_id)}, {'name': 1})
    name = p.get('name') if p else None
    log_activity(user_id, 'water', plant_id=plant_id, plant_name=name)
    return jsonify({'ok': True}), 200

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
        filename = f"{datetime.now(timezone.utc).timestamp()}_{filename}"
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
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@plants_bp.route('/search', methods=['GET'])
@jwt_required()
def search_plants():
    user_id = get_jwt_identity()
    nome = request.args.get('nome', "").strip()
    query = {'owner': user_id}
    if nome:
        query['name'] = {'$regex': nome, '$options': 'i'}
    coll = mongo.db.plants
    docs = list(coll.find(query))
    for d in docs:
        d['_id'] = str(d['_id'])
    return jsonify(docs)

@plants_bp.route('/filter', methods=['GET'])
@jwt_required()
def filter_plants():
    user_id = get_jwt_identity()
    order = request.args.get('order', "name")
    direction = -1 if request.args.get('dir', 'asc') == 'desc' else 1
    coll = mongo.db.plants
    filtro = {'owner': user_id}
    docs = list(coll.find(filtro).sort(order, direction))
    for d in docs:
        d['_id'] = str(d['_id'])
    return jsonify(docs)
