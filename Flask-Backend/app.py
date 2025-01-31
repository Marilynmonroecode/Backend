from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_migrate import Migrate
from flask_cors import CORS
from dotenv import load_dotenv
import os
from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Add your secret key for JWT (not needed anymore if you're not using JWT)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
CORS(app)
bcrypt = Bcrypt(app)
ma = Marshmallow(app)  # Flask-Marshmallow initialization

# Models
# User model
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Establish the back-population relationship with tasks
    tasks = relationship('Task', back_populates='user')

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


# Task model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    done = db.Column(db.Boolean, default=False)

    # Add the user_id column which is a ForeignKey pointing to the User table
    user_id = db.Column(db.Integer, ForeignKey('users.id'), nullable=False)

    # Set up the relationship to the User model
    user = relationship('User', back_populates='tasks')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done,
            'user_id': self.user_id
        }
    
# Marshmallow Schemas
class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = User
        load_instance = True

class TaskSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Task
        load_instance = True

# Routes

# Home route
@app.route('/')
def home():
    return jsonify({"message": "Welcome to the Task API"})

# User registration route
@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    
    # Check for missing fields
    if 'username' not in data or 'email' not in data or 'password' not in data:
        return jsonify({'error': 'Username, email, and password are required'}), 400
    
    # Check if user already exists
    existing_user = User.query.filter_by(username=data['username']).first()
    if existing_user:
        return jsonify({'error': 'Username already exists'}), 400
    
    # Create a new user
    new_user = User(
        username=data['username'],
        email=data['email'],
        password=data['password']
    )
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 200

# User login route (No JWT)
@app.route('/login', methods=['POST'])
def login_user():
    data = request.get_json()

    # Ensure required fields are present
    if 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password are required'}), 400

    # Check if user exists
    user = User.query.filter_by(username=data['username']).first()
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid username or password'}), 400
    
    # Without JWT, just return a simple success message
    return jsonify({'message': f'Welcome {user.username}! You are logged in.'}), 200

# Task routes (No JWT protection)

# Get all tasks
@app.route('/tasks', methods=['GET'])
def get_tasks():
    # Get all tasks from the database (no authentication required)
    tasks = Task.query.all()
    task_schema = TaskSchema(many=True)
    return jsonify(task_schema.dump(tasks))

# Add a new task
@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.get_json()
    
    # Ensure the required fields are present
    if 'title' not in data or 'description' not in data:
        return jsonify({'error': 'Title and description are required'}), 400
    
    # Get the user ID from the request
    user_id = data.get('user_id') 

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Create the new task with the correct user_id
    new_task = Task(
        title=data['title'],
        description=data['description'],
        done=data.get('done', False),
        user_id=user.id  # Assign the user ID to the task
    )
    
    db.session.add(new_task)
    db.session.commit()

    return jsonify(new_task.to_dict()), 200

# Get a specific task by ID
@app.route('/tasks/<int:id>', methods=['GET'])
def get_task(id):
    task = Task.query.get(id)
    if not task:
        return jsonify({"error": "Task not found"}), 400
    return jsonify(task.to_dict())

# Update a task
@app.route('/tasks/<int:id>', methods=['PUT'])
def update_task(id):
    task = Task.query.get(id)
    if not task:
        return jsonify({"error": "Task not found"}), 400

    data = request.get_json()
    
    # Update task fields
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.done = data.get('done', task.done)
    
    db.session.commit()
    return jsonify(task.to_dict())

# Delete a task
@app.route('/tasks/<int:id>', methods=['DELETE'])
def delete_task(id):
    task = Task.query.get(id)
    if not task:
        return jsonify({"error": "Task not found"}), 400
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({"message": "Task deleted"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=8080)
