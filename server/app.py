from flask import Flask, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from config import create_app, db, mail
from models import User, Inventory, Booking, Quote
from datetime import datetime
from flask_mail import Message, Mail
from sqlalchemy.exc import SQLAlchemyError

app = create_app()

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Welcome to the Movers App API. Use /auth/register to create a new account, /auth/login to log in, and other API endpoints for various functionalities.'})

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
    try:
        db.session.commit()

        # Send welcome email
        msg = Message("Welcome to Marvel Movers!", recipients=[email])
        msg.body = (
            "Dear Valued Customer,\n\n"
            "Thank you for choosing Marvel Movers! We are thrilled to have you on board. Our team is dedicated to providing you with exceptional service for all your moving needs.\n\n"
            "If you have any questions or need assistance, please do not hesitate to contact us. We look forward to helping you make your move as smooth and stress-free as possible.\n\n"
            "Best regards,\n"
            "The Marvel Movers Team\n"
            "Contact us: marvelmoverz@gmail.com\n"
        )
        try:
            mail.send(msg)
        except Exception as e:
            db.session.rollback()
            return jsonify({'message': 'User registered successfully, but failed to send welcome email.', 'error': str(e)}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'message': 'Failed to register user.', 'error': str(e)}), 500

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
    user_id = get_jwt_identity()['user_id']
    inventory = Inventory.query.filter_by(user_id=user_id).all()
    inventory_list = [{'id': item.id, 'category': item.category, 'item_name': item.item_name} for item in inventory]
    return jsonify(inventory_list), 200

@app.route('/api/inventory', methods=['POST'])
@jwt_required()
def add_inventory_item():
    data = request.json
    user_id = get_jwt_identity()['user_id']

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

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_inventory_item(item_id):
    data = request.json
    user_id = get_jwt_identity()['user_id']

    item = Inventory.query.filter_by(id=item_id, user_id=user_id).first()

    if not item:
        return jsonify({'message': 'Inventory item not found'}), 404

    category = data.get('category')
    item_name = data.get('item_name')

    if category:
        item.category = category
    if item_name:
        item.item_name = item_name

    db.session.commit()

    return jsonify({'message': 'Inventory item updated successfully', 'item': {
        'id': item.id,
        'category': item.category,
        'item_name': item.item_name
    }}), 200

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_inventory_item(item_id):
    user_id = get_jwt_identity()['user_id']
    item = Inventory.query.filter_by(id=item_id, user_id=user_id).first()

    if not item:
        return jsonify({'message': 'Inventory item not found'}), 404

    db.session.delete(item)
    db.session.commit()

    return jsonify({'message': 'Inventory item deleted successfully'}), 200

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

    # Calculate costs according to the new scheme
    packing_cost = 4000
    assembly_cost = 3000
    insurance_cost = 3000
    distance_units = distance / 5
    transportation_cost = distance_units * 700

    home_type_costs = {
        'Bedsitter': 5000,
        'One Bedroom': 6500,
        'Studio': 4500,
        'Two Bedroom': 8000,
    }

    if home_type in home_type_costs:
        room_type_cost = home_type_costs[home_type]
        total_cost = packing_cost + assembly_cost + transportation_cost + insurance_cost + room_type_cost
        user_id = get_jwt_identity()['user_id']
        quote = Quote(
            company_name='Marvel Movers',
            amount=total_cost,
            distance=distance,
            house_type=home_type,
            user_id=user_id
        )
        db.session.add(quote)
        db.session.commit()
        return jsonify({'quote': {
            'company_name': quote.company_name,
            'amount': quote.amount,
            'distance': quote.distance,
            'house_type': quote.house_type
        }}), 200
    else:
        return jsonify({'error': 'Invalid home_type.'}), 400

@app.route('/api/quote/<int:quote_id>', methods=['PUT'])
@jwt_required()
def update_quote(quote_id):
    data = request.json
    user_id = get_jwt_identity()['user_id']

    quote = Quote.query.filter_by(id=quote_id, user_id=user_id).first()

    if not quote:
        return jsonify({'message': 'Quote not found'}), 404

    distance = data.get('distance')
    home_type = data.get('home_type')

    if distance is not None:
        try:
            distance = float(distance)
            if distance < 0:
                return jsonify({'error': 'Distance cannot be negative.'}), 400
            quote.distance = distance
        except ValueError:
            return jsonify({'error': 'Distance must be a number.'}), 400

    if home_type:
        home_type_costs = {
            'Bedsitter': 5000,
            'One Bedroom': 6500,
            'Studio': 4500,
            'Two Bedroom': 8000,
        }
        if home_type in home_type_costs:
            quote.house_type = home_type
        else:
            return jsonify({'error': 'Invalid home_type.'}), 400

    packing_cost = 4000
    assembly_cost = 3000
    insurance_cost = 3000
    distance_units = quote.distance / 5
    transportation_cost = distance_units * 700

    room_type_costs = {
        'Bedsitter': 5000,
        'One Bedroom': 6500,
        'Studio': 4500,
        'Two Bedroom': 8000,
    }

    quote_amount = packing_cost + assembly_cost + transportation_cost + insurance_cost + room_type_costs.get(quote.house_type, 0)
    quote.amount = quote_amount

    db.session.commit()

    return jsonify({'message': 'Quote updated successfully', 'quote': {
        'company_name': quote.company_name,
        'amount': quote.amount,
        'distance': quote.distance,
        'house_type': quote.house_type
    }}), 200

@app.route('/api/quote/<int:quote_id>', methods=['DELETE'])
@jwt_required()
def delete_quote(quote_id):
    user_id = get_jwt_identity()['user_id']
    quote = Quote.query.filter_by(id=quote_id, user_id=user_id).first()

    if not quote:
        return jsonify({'message': 'Quote not found'}), 404

    db.session.delete(quote)
    db.session.commit()

    return jsonify({'message': 'Quote deleted successfully'}), 200

@app.route('/api/book', methods=['POST'])
@jwt_required()
def book_move():
    data = request.json
    if not data or not data.get('date') or not data.get('time'):
        return jsonify({'message': 'Invalid input'}), 400

    try:
        date_str = data['date']
        time_str = data['time']
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

@app.route('/api/select_quote', methods=['POST'])
@jwt_required()
def select_quote():
    data = request.json
    if not data or not data.get('quote_id'):
        return jsonify({'message': 'Invalid input'}), 400

    user_id = get_jwt_identity()['user_id']
    quote_id = data['quote_id']

    quote = Quote.query.filter_by(id=quote_id, user_id=user_id).first()

    if not quote:
        return jsonify({'message': 'Quote not found'}), 404

    # Save the selected quote in the database
    booking = Booking.query.filter_by(user_id=user_id).first()
    if booking:
        booking.status = 'Quote Selected'
        db.session.commit()
        return jsonify({'message': 'Quote selected successfully', 'quote': {
            'company_name': quote.company_name,
            'amount': quote.amount,
            'distance': quote.distance,
            'house_type': quote.house_type
        }}), 201

    return jsonify({'message': 'No booking found'}), 404

@app.route('/api/update_status', methods=['POST'])
@jwt_required()
def update_status():
    data = request.json
    user_id = get_jwt_identity()['user_id']
    status = data.get('status')

    if status is None:
        return jsonify({'message': 'Invalid input'}), 400

    booking = Booking.query.filter_by(user_id=user_id).first()

    if booking:
        booking.status = status
        db.session.commit()
        return jsonify({'message': 'Booking status updated'}), 200

    return jsonify({'message': 'No booking found'}), 404

@app.route('/api/track_status', methods=['GET'])
@jwt_required()
def track_status():
    user_id = get_jwt_identity()['user_id']
    booking = Booking.query.filter_by(user_id=user_id).first()

    if booking:
        return jsonify({'status': booking.status}), 200

    return jsonify({'message': 'No booking found'}), 404

@app.route('/api/admin', methods=['POST'])
@jwt_required()
def admin_tasks():
    data = request.json
    # Placeholder for admin-specific functionalities
    return jsonify({'message': 'Admin tasks completed'}), 200

@app.route('/auth/delete_account', methods=['DELETE'])
@jwt_required()
def delete_account():
    user_id = get_jwt_identity()['user_id']
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Delete related records (if needed)
    Inventory.query.filter_by(user_id=user_id).delete()
    Booking.query.filter_by(user_id=user_id).delete()
    Quote.query.filter_by(user_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'Account deleted successfully'}), 200

if __name__ == '__main__':
    app.run()