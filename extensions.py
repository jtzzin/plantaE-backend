# backend/extensions.py
# Extensões compartilhadas do Flask (MongoDB e JWT)

from flask_pymongo import PyMongo
from flask_jwt_extended import JWTManager

# Instâncias das extensões (sem app ainda)
mongo = PyMongo()
jwt = JWTManager()
