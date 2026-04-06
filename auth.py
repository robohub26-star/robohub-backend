from bson import ObjectId
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
import os
from dotenv import load_dotenv
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime

load_dotenv()

auth_bp = Blueprint("auth", __name__)

# -------------------------------
# MongoDB Setup
# -------------------------------
MONGO_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGO_URI)
db = client["learnflow"]
users_collection = db["users"]  

# ===============================
# Register Endpoint
# ===============================
@auth_bp.route("/api/register", methods=["POST"])
def register():
    data = request.json
    role = data.get("role")

    # Only allow student registration through public endpoint
    if role != "student":
        return jsonify({
            "success": False, 
            "message": "Only student registration is allowed through this endpoint"
        }), 403

    email = data.get("email")
    full_name = data.get("fullName")

    # 1. Check if user already exists based on their role
    if role == "student":
        if users_collection.find_one({"email": email, "role": "student"}):
            return jsonify({"success": False, "message": "Student with this email already exists"}), 400
    else: # role is mentor
        # Case insensitive search to see if mentor name is taken
        if users_collection.find_one({"fullName": {"$regex": f"^{full_name}$", "$options": "i"}, "role": "mentor"}):
            return jsonify({"success": False, "message": "Mentor with this name already exists"}), 400

    # 2. Build user data
    user_data = {
        "fullName": full_name,
        "email": email, 
        "phone": data.get("phone"),
        "password": generate_password_hash(data.get("password")),
        "role": role,
        "extra": data.get("extra") 
    }
    
    # 3. Add extra fields if student
    if role == "student":
        user_data["progress"] = {
            "days": {
                "1": {"completed": False, "score": None},
                "2": {"completed": False, "score": None},
                "3": {"completed": False, "score": None},
            },
        }

    users_collection.insert_one(user_data)
    return jsonify({"success": True, "message": f"{role.title()} registered successfully"})

# Add this new endpoint for admin creation
@auth_bp.route("/api/create-admin", methods=["POST"])
def create_admin():
    admin_secret = os.getenv("ADMIN_CREATION_SECRET")
    data = request.json

    if not admin_secret or data.get("adminSecret") != admin_secret:
        return jsonify({"success": False, "message": "Unauthorized"}), 403

    # Prevent duplicate admins
    if users_collection.find_one({"email": data.get("email"), "role": "mentor"}):
        return jsonify({"success": False, "message": "Admin already exists"}), 400

    user_data = {
        "fullName": data.get("fullName"),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "password": generate_password_hash(data.get("password")),
        "role": "mentor",
        "extra": data.get("extra"),
        "isApproved": True,
        "isActive": False,
        "createdAt": datetime.utcnow()
    }

    users_collection.insert_one(user_data)

    return jsonify({
        "success": True,
        "message": "Admin account created successfully"
    }), 201

# ===============================
# Login Endpoint
# ===============================
@auth_bp.route("/api/login", methods=["POST"])
def login():
    data = request.json
    role = data.get("role")
    password = data.get("password")

    if role not in ["student", "mentor"]:
        return jsonify({"success": False, "message": "Invalid role"}), 400

    # Fetch user securely
    if role == "student":
        email = data.get("email", "").strip()
        user = users_collection.find_one({"email": email, "role": "student"})
    else:
        full_name = data.get("fullName", "").strip()
        # Case-insensitive search so "Skilling" and "skilling" both work
        user = users_collection.find_one({"fullName": {"$regex": f"^{full_name}$", "$options": "i"}, "role": "mentor"})

    if not user:
        return jsonify({"success": False, "message": f"{role.title()} not found. Please sign up or check your credentials."}), 404

    if not check_password_hash(user["password"], password):
        return jsonify({"success": False, "message": "Incorrect password"}), 401

    # Set isActive to True on login
    users_collection.update_one(
        {"_id": user["_id"]},
        {"$set": {"lastLogin": datetime.utcnow(), "isActive": True}}
    )

    # Create JWT
    access_token = create_access_token(identity=str(user["_id"]))

    return jsonify({
        "success": True,
        "message": "Login successful",
        "role": role,
        "token": access_token,
        "fullName": user["fullName"]
    })


# ===============================
# Logout Endpoint
# ===============================
@auth_bp.route("/api/logout", methods=["POST"])
@jwt_required()
def logout():
    try:
        user_id = get_jwt_identity()
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"lastLogin": None, "isActive": False}}
        )
    except Exception:
        return jsonify({"success": False, "message": "Invalid userId or token"}), 400

    return jsonify({"success": True, "message": "Logged out successfully"})