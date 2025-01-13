from flask import render_template, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from passm.auth import auth_bp
from passm.db import get_db
from passm.auth.forms import LoginForm, RegistrationForm


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # Resolves the issue with missing fields in login form
    form.username = None
    form.confirm_password = None

    if form.validate_on_submit():
        db = get_db()
        cur = db.cursor(dictionary=True)

        cur.execute("SELECT * FROM user WHERE email = %s", (form.email.data,))
        user = cur.fetchone()
        print(user)

        if user is None:
            flash('No user found with that email address.', 'danger')
        elif check_password_hash(user['master_password'], form.master_password.data):
            # Successful login
            session['user_id'] = user['id']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('main.view_password_list'))
        else:
            # Invalid password
            flash('Invalid password.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{getattr(form, field).label.text}: {error}", 'danger')

    return render_template('auth/authentication.html', form=form,
                           action="login", button_label="Log In")


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    print(f"Form data: {form.data}")
    print(f"Form errors: {form.errors}")
    print(f"Form validation status: {form.validate_on_submit()}")
    if form.validate_on_submit():
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM user WHERE email = %s", (form.email.data,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Email already registered', 'danger')
        else:
            hashed_password = generate_password_hash(form.master_password.data)
            cur.execute("INSERT INTO user (email, username, master_password) VALUES (%s, %s, %s)",
                        (form.email.data, form.username.data, hashed_password))
            db.commit()

            cur.execute("SELECT * FROM user WHERE email = %s", (form.email.data,))
            user = cur.fetchone()
            cur.close()

            session['user_id'] = user['id']

            flash('Registration successful', 'success')
            return redirect(url_for('main.view_password_list'))
    return render_template('auth/authentication.html', form=form,
                           action="register", button_label="Register")


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
