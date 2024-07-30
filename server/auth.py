from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User

def register_user(data):
    username = data['username']
    email = data['email']
    password = data['password']
    hashed_password = generate_password_hash(password)
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return new_user

def authenticate_user(email, password):
    user = User.query.filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        return user
    return None
