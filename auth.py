from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User


auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/signup')
def signup():
    return render_template('signup.html')


@auth.route('/signup', methods=['POST'])
def signup_post():
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')
    # get user from database
    user = User.query.filter_by(email=email).first()
    if user:
        flash('This Mail is used by another Person')
        return redirect(url_for('auth.signup'))
    # If not User found Create new
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))
    #commit
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))


@auth.route('/logout')
def logout():
    return 'Logout'