from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timezone, timedelta
from extensions import mongo
from bson import ObjectId

activities_bp = Blueprint('activities', __name__)

def convert_objid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {k: convert_objid(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [convert_objid(x) for x in obj]
    return obj

def log_activity(owner: str, action: str, plant_id: str = None, plant_name: str = None, extra: dict = None):
    doc = {
        'owner': owner,
        'action': action,
        'plant_id': plant_id,
        'plant_name': plant_name,
        'at': datetime.now(timezone.utc),
    }
    if extra:
        doc['extra'] = extra
    mongo.db.activities.insert_one(doc)

@activities_bp.route('/', methods=['GET'])
@jwt_required()
def list_activities():
    user_id = get_jwt_identity()
    q = {'owner': user_id}

    plant_id = request.args.get('plant_id', '').strip()
    if plant_id:
        q['plant_id'] = plant_id

    day = request.args.get('day', '').strip()
    if day:
        try:
            start = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
            end = start + timedelta(days=1)
            q['at'] = {'$gte': start, '$lt': end}
        except Exception:
            pass

    cursor = mongo.db.activities.find(q).sort('at', -1)
    docs = []
    for d in cursor:
        d = convert_objid(d)
        d['at'] = d['at'].isoformat()
        docs.append(d)
    return jsonify(docs), 200
