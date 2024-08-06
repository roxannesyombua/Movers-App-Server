from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import create_app, db
from models import User, Inventory, Booking, Quote, HomeType
from datetime import datetime

# Create the Flask app using the factory function
app = create_app()

@app.route('/')
def home():
    return jsonify({'message': 'Welcome to the Movers App API'}), 200

@app.route('/auth/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already registered'}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(
        username=data.get('username'),
        email=email,
        password=hashed_password,
        role=data.get('role', 'client')
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully', 'user_id': new_user.id}), 201

@app.route('/auth/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        access_token = create_access_token(identity={'user_id': user.id, 'role': user.role})
        return jsonify({'message': 'Login successful', 'access_token': access_token}), 200

    return jsonify({'message': 'Invalid credentials'}), 401

@app.route('/api/inventory', methods=['GET'])
@jwt_required()
def get_inventory():
    identity = get_jwt_identity()
    role = identity['role']
    user_id = identity['user_id']
    
    if role == 'admin':
        inventory = Inventory.query.all()
    else:
        inventory = Inventory.query.filter_by(user_id=user_id).all()

    inventory_list = [
        {
            'id': item.id,
            'category': item.category,
            'item_name': item.item_name,
            'price': item.price
        } for item in inventory
    ]
    return jsonify(inventory_list), 200

@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_inventory_item():
    data = request.json
    user_id = get_jwt_identity()['user_id']
    
    category = data.get('category')
    item_name = data.get('item_name')
    price = data.get('price')

    if not category or not item_name or price is None:
        return jsonify({'message': 'Category, item name, and price are required'}), 400

    new_item = Inventory(category=category, item_name=item_name, price=price, user_id=user_id)
    db.session.add(new_item)
    db.session.commit()
    return jsonify({'message': 'Inventory item added successfully', 'item': {
        'id': new_item.id,
        'category': new_item.category,
        'item_name': new_item.item_name,
        'price': new_item.price
    }}), 201

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
        item.price = data['price']

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
    current_location = data.get('current_location')
    new_location = data.get('new_location')

    if not current_location or not new_location:
        return jsonify({'message': 'Current location and new location are required'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking(user_id=user_id, current_location=current_location, new_location=new_location, status='Pending')
    db.session.add(booking)
    db.session.commit()
    return jsonify({'message': 'Location details saved'}), 201

@app.route('/api/quote', methods=['POST'])
@jwt_required()
def approve_quote():
    data = request.json
    approve = data.get('approve')

    if approve is None:
        return jsonify({'message': 'Approval status is required'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id).first()
    if booking:
        booking.approved = approve
        booking.status = 'Approved' if approve else 'Rejected'
        db.session.commit()
        return jsonify({'message': 'Quote updated', 'approved': approve}), 200

    return jsonify({'message': 'No booking found'}), 404

@app.route('/api/book', methods=['POST'])
@jwt_required()
def book_move():
    data = request.json
    date_str = data.get('date')
    time_str = data.get('time')

    if not date_str or not time_str:
        return jsonify({'message': 'Date and time are required'}), 400

    try:
        booking_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        booking_time = datetime.strptime(time_str, '%H:%M').time()
    except ValueError:
        return jsonify({'message': 'Invalid date or time format'}), 400

    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id, approved=True).first()
    if booking:
        booking.date = booking_date
        booking.time = booking_time
        booking.status = 'Confirmed'
        db.session.commit()
        return jsonify({'message': 'Booking confirmed'}), 200

    return jsonify({'message': 'No approved booking found'}), 404

@app.route('/api/bookings', methods=['GET'])
@jwt_required()
def view_bookings():
    identity = get_jwt_identity()
    user_id = identity['user_id']
    role = identity['role']
    
    if role == 'admin':
        bookings = Booking.query.all()
    else:
        bookings = Booking.query.filter_by(user_id=user_id).all()

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
    data = request.json
    move_request_id = data.get('move_request_id')

    if not move_request_id:
        return jsonify({'message': 'Move request ID is required'}), 400

    user_id = get_jwt_identity()['user_id']
    
    # Simulate notification sending logic
    # Replace with actual notification logic (e.g., email or SMS)
    # Example:
    # user = User.query.get(user_id)
    # send_email(user.email, 'Move Request Confirmed', f'Your move request {move_request_id} has been confirmed.')

    return jsonify({'message': f'Notification for move request {move_request_id} sent'}), 200

@app.route('/api/calculate_quote', methods=['POST'])
@jwt_required()
def calculate_quote():
    data = request.json
    distance = data.get('distance')
    home_type = data.get('home_type')
    custom_calculations = data.get('custom_calculations', [])

    if distance is None or home_type is None:
        return jsonify({'error': 'Distance and home_type are required.'}), 400

    try:
        distance = float(distance)
    except ValueError:
        return jsonify({'error': 'Distance must be a number.'}), 400

    if distance < 0:
        return jsonify({'error': 'Distance cannot be negative.'}), 400

    companies = [
        {'name': 'Company A', 'base_rate': 150, 'distance_rate': 4},
        {'name': 'Company B', 'base_rate': 200, 'distance_rate': 5},
        {'name': 'Company C', 'base_rate': 180, 'distance_rate': 4.5},
        {'name': 'Company D', 'base_rate': 170, 'distance_rate': 4.2}
    ]

    home_type_rates = {
        'Bedsitter': 50,
        'One Bedroom': 100,
        'Studio': 80,
        'Two Bedroom': 120,
    }

    quotes = []
    if home_type in home_type_rates:
        for company in companies:
            base_rate = company['base_rate'] + home_type_rates[home_type]
            amount = base_rate + (distance * company['distance_rate'])
            
            # Apply custom calculations
            for calc in custom_calculations:
                if calc.get('company') == company['name']:
                    amount += calc.get('additional_amount', 0)

            quote_id = len(quotes) + 1
            quotes.append({
                'quote_id': quote_id,
                'company': company['name'],
                'base_rate': base_rate,
                'distance_cost': distance * company['distance_rate'],
                'total_amount': amount
            })
    else:
        return jsonify({'error': 'Invalid home type.'}), 400

    return jsonify({'quotes': quotes}), 200

@app.route('/api/home_types', methods=['GET'])
@jwt_required()
def get_home_types():
    home_types = HomeType.query.all()
    return jsonify([home_type.name for home_type in home_types]), 200

if __name__ == '__main__':
    app.run(debug=True)
