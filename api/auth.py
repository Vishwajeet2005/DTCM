from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
from db.models import Users
from config import config

auth_bp = Blueprint('auth', __name__)

# Note: Requires active SQLAlchemy session from the app context
# We'll use a db object that will be initialized in app.py
from app_db import db

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''
    role = data.get('role', 'general')
    name = (data.get('name') or '').strip()

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    valid_roles = ['administrator', 'environmental_authority', 'researcher', 'general']
    if role not in valid_roles:
        role = 'general'

    if db.session.query(Users).filter_by(Email=email).first():
        return jsonify({"msg": "An account with this email address already exists"}), 400

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
    
    new_user = Users(
        Email=email, 
        PasswordHash=hashed.decode('utf-8'), 
        Role=role, 
        Name=name or email.split('@')[0]
    )
    db.session.add(new_user)
    db.session.commit()
    
    access_token = create_access_token(identity=str(new_user.UserID))
    return jsonify({
        "msg": "User created successfully",
        "user_id": new_user.UserID,
        "access_token": access_token,
        "role": new_user.Role,
        "name": new_user.Name,
        "email": new_user.Email
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"msg": "Email and password required"}), 400

    user = db.session.query(Users).filter_by(Email=email).first()
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user.PasswordHash.encode('utf-8')):
        return jsonify({"msg": "Bad email or password"}), 401

    access_token = create_access_token(identity=str(user.UserID))
    return jsonify({
        "access_token": access_token,
        "role": user.Role,
        "name": user.Name,
        "email": user.Email,
        "user_id": user.UserID
    })

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    current_user_id = get_jwt_identity()
    try:
        user = db.session.get(Users, int(current_user_id))
    except (ValueError, TypeError):
        user = None
        
    if not user:
        return jsonify({"msg": "User not found"}), 404
        
    return jsonify({
        "user_id": user.UserID,
        "name": user.Name,
        "email": user.Email,
        "role": user.Role
    })

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({"msg": "Successfully logged out"}), 200
