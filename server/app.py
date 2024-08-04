from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import create_app, db
from models import User, Inventory, Booking
from datetime import datetime

# Create the Flask app using the factory function
app = create_app()

@app.route('/')
def home():
    return jsonify({'message': 'Welcome to the Movers App API'}), 200

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
        access_token = create_access_token(identity={'user_id': user.id, 'role': user.role})
        return jsonify({'message': 'Login successful', 'access_token': access_token}), 200

    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/inventory', methods=['GET'])
@jwt_required()
def get_inventory():
    inventory = Inventory.query.all()
    inventory_list = [
        {
            'id': item.id,
            'category': item.category,
            'item_name': item.item_name,
            'price': item.price  # Include price in response
        } for item in inventory
    ]
    return jsonify(inventory_list), 200

@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_inventory():
    data = request.json
    if not data or not data.get('category') or not data.get('item_name') or not data.get('price'):
        return jsonify({'message': 'Invalid input'}), 400

    new_item = Inventory(category=data['category'], item_name=data['item_name'], price=data['price'])
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'message': 'Item added', 'item_id': new_item.id}), 201

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_inventory(item_id):
    data = request.json
    item = Inventory.query.get(item_id)
    if not item:
        return jsonify({'message': 'Item not found'}), 404

    if 'category' in data:
        item.category = data['category']
    if 'item_name' in data:
        item.item_name = data['item_name']
    if 'price' in data:
        item.price = data['price']  # Update price if provided

    db.session.commit()
    return jsonify({'message': 'Item updated'}), 200

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_inventory(item_id):
    item = Inventory.query.get(item_id)
    if not item:
        return jsonify({'message': 'Item not found'}), 404

    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item deleted'}), 200

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

    try:
        # Parse date and time
        booking_date = datetime.strptime(data['date'], '%Y-%m-%d')
        booking_time = datetime.strptime(data['time'], '%H:%M:%S').time()
        user_id = get_jwt_identity()['user_id']
        booking = Booking.query.filter_by(user_id=user_id, approved=True).first()
        if booking:
            booking.date = booking_date
            booking.time = booking_time
            booking.status = 'confirmed'  # Updated status field
            db.session.commit()
            return jsonify({'message': 'Booking confirmed'}), 200

        return jsonify({'message': 'No approved booking found'}), 404
    except ValueError:
        return jsonify({'message': 'Invalid date or time format'}), 400

@app.route('/api/bookings', methods=['GET'])
@jwt_required()
def view_bookings():
    user_id = get_jwt_identity()['user_id']
    role = get_jwt_identity()['role']
    
    if role == 'admin':
        bookings = Booking.query.all()  # Admin can see all bookings
    else:
        bookings = Booking.query.filter_by(user_id=user_id).all()  # Users see their own bookings

    bookings_list = [
        {
            'id': booking.id,
            'current_location': booking.current_location,
            'new_location': booking.new_location,
            'date': booking.date.strftime('%Y-%m-%d') if booking.date else None,
            'time': booking.time.strftime('%H:%M:%S') if booking.time else None,
            'approved': booking.approved,
            'status': booking.status
        } for booking in bookings
    ]
    
    return jsonify(bookings_list), 200

@app.route('/api/notify', methods=['POST'])
@jwt_required()
def notify():
    # Placeholder for sending notifications
    return jsonify({'message': 'Notification sent'}), 200

if __name__ == '__main__':
    app.run(debug=True)
