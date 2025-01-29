from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)

# Models
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    done = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done
        }

# Routes
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Task API"})

@app.route('/tasks', methods=['GET'])
def get_tasks():
    tasks = Task.query.all()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/tasks', methods=['POST'])
def add_task():
    try:
        # Get data from request body
        data = request.get_json()

        # Print incoming request data for debugging
        print(f"Received data: {data}")

        # Ensure the data has necessary fields
        if 'title' not in data or 'description' not in data:
            return jsonify({'error': 'Title and description are required'}), 400

        # Create new task and add it to the database
        new_task = Task(
            title=data['title'],
            description=data['description'],
            done=data.get('done', False)  # Default to False if not provided
        )
        
        db.session.add(new_task)
        db.session.commit()

        # Print the task after it's added to the database for debugging
        print(f"Created task: {new_task.to_dict()}")

        # Return the newly added task as JSON with a 200 status code
        return jsonify(new_task.to_dict()), 200

    except Exception as e:
        # Print the error message
        print(f"Error adding task: {e}")
        return jsonify({'error': 'Internal Server Error'}), 500

@app.route('/tasks/<int:id>', methods=['GET'])
def get_task(id):
    task = Task.query.get(id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
    return jsonify(task.to_dict())

@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    task = Task.query.get(id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
        
    data = request.get_json()
    
    # Update task fields
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.done = data.get('done', task.done)
    
    db.session.commit()
    
    return jsonify(task.to_dict())

@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = Task.query.get(id)
    if task is None:
        return jsonify({"error": "Task not found"}), 404
        
    db.session.delete(task)
    db.session.commit()
    
    return '', 204  # Return No Content status on successful deletion

if __name__ == '__main__':
    app.run(debug=True, port=5001)
