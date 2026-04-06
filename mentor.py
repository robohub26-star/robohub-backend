from flask import Blueprint, jsonify
from pymongo import MongoClient
from bson import ObjectId
import os
from dotenv import load_dotenv
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta

# ===============================
# Environment Variables & Setup
# ===============================
# Load environment variables from the .env file
load_dotenv()

# Create a Flask Blueprint for mentor-related routes
mentor_bp = Blueprint("mentor", __name__, url_prefix="/mentor")

# ===============================
# MongoDB Connection Setup
# ===============================
# Fetch the MongoDB connection string and initialize the client
MONGO_URI = os.getenv("MONGODB_URI")
client = MongoClient(MONGO_URI)
db = client["learnflow"]
users_collection = db["users"]

# ===============================
# Mentor Dashboard Endpoint
# ===============================
@mentor_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def mentor_dashboard():
    """
    GET Endpoint: Fetches dashboard statistics for the mentor.
    Requires a valid JWT token. It retrieves all students, calculates their
    individual progress and average scores, and returns an aggregated overview.
    """
    
    # 1. Determine mentor's full name from JWT identity
    mentor_name = "Mentor"
    try:
        # Extract the mentor's ID from the provided JWT token
        mentor_id = get_jwt_identity()
        if mentor_id:
            # Query the database to find the mentor's user document
            mentor_user = users_collection.find_one({"_id": ObjectId(mentor_id)})
            if mentor_user and mentor_user.get("fullName"):
                mentor_name = mentor_user.get("fullName")
    except Exception:
        # Fallback to default mentor name if token extraction or DB lookup fails
        mentor_name = "Mentor"

    # 2. Fetch all students from the database
    students_cursor = users_collection.find({"role": "student"})
    students_list = []
    
    # Initialize dashboard aggregate counters
    total_students = 0
    active_students = 0
    tests_reviewed = 0

    # 3. Process each student's data
    for student in students_cursor:
        total_students += 1
        
        # Check if the student is currently active
        is_active = student.get("isActive", False)
        if is_active:
            active_students += 1

        # Extract the student's progress data
        progress = student.get("progress", {}).get("days", {})
        
        # Create a list of days that have been marked as completed
        completed_days = [int(day) for day, info in progress.items() if info.get("completed")]

        # Determine the last completed day for display purposes
        if completed_days:
            last_day_num = max(completed_days)
            last_day = f"Day {last_day_num}"
        else:
            last_day = "N/A"

        # --- UPDATED LOGIC HERE ---
        # Calculate the average score across ALL completed days
        scores = [info.get("score", 0) for _, info in progress.items() if info.get("completed")]
        score = round(sum(scores) / len(scores)) if scores else 0
        
        # Calculate progress percentage (based on a 3-day course)
        progress_percent = round(len(completed_days) / 3 * 100)
        # --------------------------

        # Increment total tests reviewed based on the number of completed days
        tests_reviewed += len(completed_days)

        # Append the formatted student data to our list
        students_list.append({
            "fullName": student.get("fullName"),
            "email": student.get("email"),
            "progressPercent": progress_percent,
            "lastDay": last_day,
            "score": score,
            "isActive": is_active
        })

    # 4. Construct the final JSON response payload
    response = {
        "fullName": mentor_name,
        "totalCourses": 1,
        "totalStudents": total_students,
        "activeStudents": active_students,
        "testsReviewed": tests_reviewed,
        "students": students_list
    }

    # Return the response to the client
    return jsonify(response)