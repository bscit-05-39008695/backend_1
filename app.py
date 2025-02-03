from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_marshmallow import Marshmallow
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import marshmallow_sqlalchemy



app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    "database": "postgres",
    "user": "postgres.nzqybfjrmlsbrskzbyil",
    "password": "WMBqWdQO4TYIx8MM",
    "host": "aws-0-ap-south-1.pooler.supabase.com",
    "port": 5432
}

# Set up database URI for SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure connection pooling
app.config['SQLALCHEMY_POOL_SIZE'] = 10
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 5
app.config['SQLALCHEMY_POOL_RECYCLE'] = 3600

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
ma = Marshmallow(app)

# Initialize CORS
CORS(app)

# User model
class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(250), nullable=False, unique=True)
    password = db.Column(db.String(300), nullable=False)

# Expense model
class Expense(db.Model):
    __tablename__ = 'expenses'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    description = db.Column(db.String(300), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    user = db.relationship('Role', backref=db.backref('expenses', lazy=True))

# Schemas
class RoleSchema(marshmallow_sqlalchemy.SQLAlchemyAutoSchema):
    class Meta:
        model = Role
        fields = ('id', 'email')

class ExpenseSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Expense
        fields = ('id', 'description', 'amount', 'user_id')

# Initialize schemas
role_schema = RoleSchema()
roles_schema = RoleSchema(many=True)
expense_schema = ExpenseSchema()
expenses_schema = ExpenseSchema(many=True)

@app.route('/')
def hello_world():
    return 'Hello, World!'

# Register route
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        
        if not all(key in data for key in ['email', 'password', 'confirm_password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if data['password'] != data['confirm_password']:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        existing_user = Role.query.filter_by(email=data['email']).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create user without storing confirm_password
        new_user = Role(
            email=data['email'],
            password=generate_password_hash(data['password'])
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'Registration successful',
            'user': role_schema.dump(new_user)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Login route
@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        
        if not all(key in data for key in ['email', 'password']):
            return jsonify({'error': 'Missing required fields'}), 400
        
        user = Role.query.filter_by(email=data['email']).first()
        
        if user and check_password_hash(user.password, data['password']):
            return jsonify({
                'message': 'Login successful',
                'user': role_schema.dump(user)
            }), 200
        
        return jsonify({'error': 'Invalid email or password'}), 401
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Add an expense route
@app.route('/add_expense', methods=['POST'])
def add_expense():
    try:
        data = request.json

        if not all(key in data for key in ['description', 'amount', 'user_id']):
            return jsonify({'error': 'Missing required fields'}), 400

        new_expense = Expense(
            description=data['description'],
            amount=data['amount'],
            user_id=data['user_id']
        )

        db.session.add(new_expense)
        db.session.commit()

        return jsonify({
            'message': 'Expense added successfully',
            'expense': expense_schema.dump(new_expense)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# Delete an expense route
@app.route('/delete_expense/<int:expense_id>', methods=['DELETE'])
def delete_expense(expense_id):
    try:
        expense = Expense.query.get(expense_id)
        
        if not expense:
            return jsonify({'error': 'Expense not found'}), 404
        
        db.session.delete(expense)
        db.session.commit()

        return jsonify({'message': 'Expense deleted successfully'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure the database tables are created
    app.run(port=5002, debug=True)
