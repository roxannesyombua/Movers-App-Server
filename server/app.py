from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import create_app, db
from models import User, Inventory, Booking
from datetime import datetime, date, time

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

@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_inventory_item():
    data = request.json

    # Extract data
    category = data.get('category')
    item_name = data.get('item_name')

    # Basic validation
    if not category or not item_name:
        return jsonify({'message': 'Category and item name are required'}), 400

    # Create and add new inventory item
    new_item = Inventory(category=category, item_name=item_name)
    db.session.add(new_item)
    db.session.commit()

    return jsonify({'message': 'Inventory item added successfully', 'item': {
        'id': new_item.id,
        'category': new_item.category,
        'item_name': new_item.item_name
    }}), 201

@app.route('/api/location', methods=['POST'])
@jwt_required()
def share_location():
    data = request.json
    if not data or not data.get('current_location') or not data.get('new_location'):
        return jsonify({'message': 'Invalid input'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking(user_id=user_id, current_location=data['current_location'], new_location=data['new_location'], status="Pending")
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
        if data['approve']:
            booking.status = 'Approved'
        else:
            booking.status = 'Rejected'
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
        # Convert date and time from strings to Python date and time objects
        date_str = data['date']
        time_str = data['time']

        # Convert the date and time strings to date and time objects
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        time_obj = datetime.strptime(time_str, '%H:%M').time()

    except ValueError as e:
        return jsonify({'message': 'Invalid date or time format', 'error': str(e)}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id, approved=True).first()

    if booking:
        booking.date = date_obj
        booking.time = time_obj
        booking.status = 'Confirmed'
        db.session.commit()
        return jsonify({'message': 'Booking confirmed'}), 200

    return jsonify({'message': 'No approved booking found'}), 404

@app.route('/api/notify', methods=['POST'])
@jwt_required()
def notify():
    # Placeholder for sending notifications
    return jsonify({'message': 'Notification sent'}), 200

@app.route('/api/calculate_quote', methods=['POST'])
@jwt_required()
def calculate_quote():
    data = request.json

    # Extract details like distance, volume
    distance = data.get('distance')
    volume = data.get('volume')

    # Basic validation
    if distance is None or volume is None:
        return jsonify({'error': 'Distance and volume are required.'}), 400

    try:
        distance = float(distance)
        volume = float(volume)
    except ValueError:
        return jsonify({'error': 'Distance and volume must be numbers.'}), 400

    # Check for negative values
    if distance < 0 or volume < 0:
        return jsonify({'error': 'Distance and volume cannot be negative.'}), 400

    # Use an algorithm to calculate the cost
    base_rate = 100  # Base rate for the service
    distance_rate = 5  # Rate per km
    volume_rate = 2  # Rate per cubic meter

    amount = base_rate + (distance * distance_rate) + (volume * volume_rate)

    return jsonify({'amount': amount}), 200

@app.route('/api/update_status', methods=['POST'])
@jwt_required()
def update_status():
    data = request.json
    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id).first()
    
    if not booking:
        return jsonify({'message': 'No booking found'}), 404
    
    booking.status = data.get('status')
    db.session.commit()
    return jsonify({'message': 'Status updated'}), 200

@app.route('/api/get_status', methods=['GET'])
@jwt_required()
def get_status():
    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id).first()
    
    if not booking:
        return jsonify({'message': 'No booking found'}), 404
    
    return jsonify({'status': booking.status}), 200

if __name__ == '__main__':
    app.run(debug=True)
