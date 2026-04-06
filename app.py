from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from dotenv import load_dotenv
import random
from auth import auth_bp
from progress import progress_bp
from flask_jwt_extended import JWTManager
from mentor import mentor_bp

# ===============================
# Load environment variables
# ===============================
load_dotenv()

# ===============================
# Flask App Setup
# ===============================
app = Flask(__name__)
CORS(app)

# JWT setup
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-key")
jwt = JWTManager(app)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(progress_bp)
app.register_blueprint(mentor_bp)

# ===============================
# Training Days Data
# ===============================
TRAINING_DAYS = [
    {"day": 1, "topics": "ROS2 Basics, Ubuntu, Nodes, Topics, Publisher/Subscriber, Turtlesim"},
    {"day": 2, "topics": "Robot Structure, TF, Frame Hierarchy, URDF, RViz, Gazebo Simulation"},
    {"day": 3, "topics": "SLAM, Mapping, Nav2 Navigation, TortoiseBot, Teleop, rqt_graph"}
]

# ===============================
# Get Questions — randomly picks 15 from 50 per level, shuffled every time
# ===============================
def get_sample_questions(day, level, count=15):
    file_path = os.path.join(os.path.dirname(__file__), f"day{day}_questions.json")

    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            data = json.load(f)

        # Get questions for requested level, fallback to beginner
        level_data = data.get(level.lower(), data.get("beginner", {}))
        all_mcqs = level_data.get("mcqs", [])

        if not all_mcqs:
            return {"error": f"No questions found for level '{level}' in day {day}"}

        # Shuffle first, then pick 'count' questions — fresh order every request
        shuffled = all_mcqs.copy()
        random.shuffle(shuffled)
        sampled_mcqs = shuffled[:min(count, len(shuffled))]

        return {
            "day": day,
            "level": level,
            "total_available": len(all_mcqs),
            "count": len(sampled_mcqs),
            "mcqs": sampled_mcqs
        }

    # Hard fallback if JSON file not found
    return {
        "error": f"day{day}_questions.json not found",
        "mcqs": [
            {
                "question": "Fallback MCQ?",
                "options": {"A": "Yes", "B": "No", "C": "Maybe", "D": "None"},
                "correct": "A"
            }
        ]
    }


# ===============================
# Generate Questions Route
# POST /api/generate-questions
# Body: { "day": 1, "level": "beginner" | "intermediate" | "advanced" }
# ===============================
@app.route("/api/generate-questions", methods=["POST"])
def generate_questions():
    data = request.json

    day = data.get("day", 1)
    level = data.get("level", "beginner")

    # Validate day
    if day not in [1, 2, 3]:
        return jsonify({"error": "Invalid day. Must be 1, 2, or 3."}), 400

    # Validate level
    if level.lower() not in ["beginner", "intermediate", "advanced"]:
        return jsonify({"error": "Invalid level. Must be beginner, intermediate, or advanced."}), 400

    result = get_sample_questions(day, level)

    if "error" in result and "mcqs" not in result:
        return jsonify(result), 404

    return jsonify(result), 200


# ===============================
# Final Assessment Route
# GET /api/final-assessment
# ===============================
@app.route("/api/final-assessment", methods=["GET"])
def get_final_assessment():
    try:
        file_path = os.path.join(os.path.dirname(__file__), "final.json")

        if not os.path.exists(file_path):
            return jsonify({"error": "final.json not found"}), 404

        with open(file_path, "r") as f:
            data = json.load(f)

        questions = data.get("theory", [])

        if len(questions) < 5:
            return jsonify({"error": "Not enough questions in final.json"}), 400

        # Shuffle and pick 5 fresh every time
        shuffled = questions.copy()
        random.shuffle(shuffled)
        selected_questions = shuffled[:5]

        return jsonify({
            "total_available": len(questions),
            "count": len(selected_questions),
            "theory": selected_questions
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ===============================
# Health Check
# GET /api/health
# ===============================
@app.route("/api/health")
def health():
    return jsonify({"status": "OK"})


# ===============================
# Run Server
# ===============================
if __name__ == "__main__":
    print("🚀 Backend running at http://localhost:5000")
    app.run(debug=True)