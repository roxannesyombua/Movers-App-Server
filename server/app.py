# app.py

from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import create_app, db
from models import User, Inventory, Booking

app = create_app()

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Invalid input'}), 400

    email = data['email']
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 409

    password = data['password']
    hashed_password = generate_password_hash(password)
    new_user = User(username=data.get('username'), email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Invalid input'}), 400

    email = data['email']
    password = data['password']
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity={'user_id': user.id})
        return jsonify({'message': 'Login successful', 'access_token': access_token}), 200

    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/inventory', methods=['GET'])
@jwt_required()
def get_inventory():
    inventory = Inventory.query.all()
    inventory_list = [{'id': item.id, 'category': item.category, 'item_name': item.item_name} for item in inventory]
    return jsonify(inventory_list), 200

@app.route('/api/location', methods=['POST'])
@jwt_required()
def share_location():
    data = request.json
    if not data or not data.get('current_location') or not data.get('new_location'):
        return jsonify({'message': 'Invalid input'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking(user_id=user_id, current_location=data['current_location'], new_location=data['new_location'])
    db.session.add(booking)
    db.session.commit()
    return jsonify({'message': 'Location details saved'}), 201

@app.route('/api/quote', methods=['POST'])
@jwt_required()
def approve_quote():
    data = request.json
    if not data or 'approve' not in data:
        return jsonify({'message': 'Invalid input'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id).first()
    if booking:
        booking.approved = data['approve']
        db.session.commit()
        return jsonify({'message': 'Quote updated', 'approved': data['approve']}), 200

    return jsonify({'message': 'No booking found'}), 404

@app.route('/api/book', methods=['POST'])
@jwt_required()
def book_move():
    data = request.json
    if not data or not data.get('date') or not data.get('time'):
        return jsonify({'message': 'Invalid input'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id, approved=True).first()
    if booking:
        booking.date = data['date']
        booking.time = data['time']
        db.session.commit()
        return jsonify({'message': 'Booking confirmed'}), 200

    return jsonify({'message': 'No approved booking found'}), 404

@app.route('/api/notify', methods=['POST'])
@jwt_required()
def notify():
    # Placeholder for sending notifications
    return jsonify({'message': 'Notification sent'}), 200

if __name__ == '__main__':
    app.run(debug=True)
