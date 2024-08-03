from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import create_app, db
from models import User, Inventory, Booking, Quote
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
    user_id = get_jwt_identity()['user_id']  # Get the ID of the logged-in user
    inventory = Inventory.query.filter_by(user_id=user_id).all()  # Filter by user_id
    inventory_list = [{'id': item.id, 'category': item.category, 'item_name': item.item_name} for item in inventory]
    return jsonify(inventory_list), 200


@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_inventory_item():
    data = request.json
    user_id = get_jwt_identity()['user_id']  # Get the ID of the logged-in user

    category = data.get('category')
    item_name = data.get('item_name')

    if not category or not item_name:
        return jsonify({'message': 'Category and item name are required'}), 400

    new_item = Inventory(category=category, item_name=item_name, user_id=user_id)
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

    distance = data.get('distance')
    home_type = data.get('home_type')

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
            quote_id = len(quotes) + 1  # Simple ID for demonstration
            quotes.append({
                'quote_id': quote_id,
                'company': company['name'],
                'amount': amount,
                'distance': distance,
                'home_type': home_type
            })
    else:
        return jsonify({'error': 'Invalid home_type.'}), 400

    return jsonify({'quotes': quotes}), 200

@app.route('/api/select_quote', methods=['POST'])
@jwt_required()
def select_quote():
    data = request.json
    if not data or not data.get('quote_id'):
        return jsonify({'message': 'Invalid input'}), 400

    user_id = get_jwt_identity()['user_id']
    quote_id = data['quote_id']

    # Retrieve the quote details using the quote_id
    quotes = [
        {'quote_id': 1, 'company': 'Company A', 'amount': 350, 'distance': 50, 'home_type': 'One Bedroom'},
        {'quote_id': 2, 'company': 'Company B', 'amount': 400, 'distance': 50, 'home_type': 'One Bedroom'},
        {'quote_id': 3, 'company': 'Company C', 'amount': 380, 'distance': 50, 'home_type': 'One Bedroom'},
        {'quote_id': 4, 'company': 'Company D', 'amount': 370, 'distance': 50, 'home_type': 'One Bedroom'}
    ]
    selected_quote = next((quote for quote in quotes if quote['quote_id'] == quote_id), None)

    if not selected_quote:
        return jsonify({'message': 'Quote not found'}), 404

    # Save the selected quote in the database
    new_quote = Quote(
        company_name=selected_quote['company'],
        amount=selected_quote['amount'],
        distance=selected_quote['distance'],
        house_type=selected_quote['home_type'],
        user_id=user_id
    )
    db.session.add(new_quote)
    db.session.commit()

    return jsonify({'message': 'Quote selected successfully', 'quote': {
        'company_name': new_quote.company_name,
        'amount': new_quote.amount,
        'distance': new_quote.distance,
        'house_type': new_quote.house_type
    }}), 201

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
