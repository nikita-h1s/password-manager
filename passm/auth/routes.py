from flask import render_template, redirect, url_for, session, flash, request, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
from passm.auth import auth_bp
from passm.db import get_db
from passm.auth.forms import LoginForm, RegistrationForm
from passm.utils import login_required, generate_totp_secret, generate_qr_code, verify_totp_code


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        db = get_db()
        cur = db.cursor(dictionary=True)

        # Check if the user exists
        cur.execute("SELECT * FROM user WHERE email = %s", (form.email.data,))
        user = cur.fetchone()

        if user is None:
            flash('No user found with that email address.', 'danger')
        elif check_password_hash(user['master_password'], form.master_password.data):
            cur.execute("""
                        SELECT tfa.status, tfa.totp_secret
                        FROM user AS u
                        JOIN user_configuration AS uc ON u.id = uc.user_id
                        JOIN two_factor_auth AS tfa ON uc.user_configuration_id = tfa.user_configuration_id
                        WHERE u.id = %s;
                        """, (user['id'],))
            tfa_status = cur.fetchone()

            if tfa_status and tfa_status['status']:
                # 2FA is enabled for the user
                if not form.totp_code.data:
                    flash('Please enter the 2FA code.', 'danger')
                else:
                    # Verify the provided 2FA code
                    if verify_totp_code(tfa_status['totp_secret'], form.totp_code.data):
                        # Successful 2FA verification
                        session['user_id'] = user['id']
                        session['username'] = user['username']
                        session['email'] = user['email']
                        flash('Logged in successfully!', 'success')
                        return redirect(url_for('main.view_password_list'))
                    else:
                        flash('Invalid 2FA code.', 'danger')
            else:
                # 2FA is not enabled; proceed to login
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['email'] = user['email']
                flash('Logged in successfully!', 'success')
                return redirect(url_for('main.view_password_list'))
        else:
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

            cur.execute("INSERT INTO vault (vault_name, vault_description, user_id) VALUES (%s, %s, %s)",
                        ("Personal", "Vault for personal resources.", user['id']))

            cur.execute(
                "INSERT INTO user_configuration (automatic_logout_time, two_factor_auth, "
                "show_passwords_by_default, user_id) VALUES (%s, %s, %s, %s)",
                (60, False, False, user['id'])
            )

            # Retrieve the user_configuration_id
            cur.execute("SELECT user_configuration_id FROM user_configuration WHERE user_id = %s", (user['id'],))
            user_config = cur.fetchone()

            # Generate TOTP secret and insert into two_factor_auth table
            totp_secret = generate_totp_secret()  # Define this helper function
            cur.execute(
                "INSERT INTO two_factor_auth (auth_type, status, user_configuration_id, totp_secret) "
                "VALUES (%s, %s, %s, %s)",
                ('TOTP', False, user_config['user_configuration_id'], totp_secret)
            )

            db.commit()
            cur.close()

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['email'] = user['email']

            flash('Registration successful', 'success')
            return redirect(url_for('main.view_password_list'))
    return render_template('auth/authentication.html', form=form,
                           action="register", button_label="Register")


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


@auth_bp.route('/generate-qr', methods=['GET'])
@login_required
def generate_qr():
    user_id = session['user_id']
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
            SELECT tfa.totp_secret
            FROM user AS u
            JOIN user_configuration AS uc ON u.id = uc.user_id
            JOIN two_factor_auth AS tfa ON uc.user_configuration_id = tfa.user_configuration_id
            WHERE u.id = %s;""", (user_id,))

    secret = cur.fetchone()

    return generate_qr_code(session['username'], secret['totp_secret'])


@auth_bp.route('/update-2fa', methods=['POST'])
@login_required
def update_2fa():
    user_id = session['user_id']
    enable_2fa = request.form.get('allow_2fa') == 'on'

    db = get_db()
    cur = db.cursor(dictionary=True)

    try:
        if enable_2fa:
            cur.execute("""
                UPDATE two_factor_auth AS tfa
                JOIN user_configuration AS uc ON tfa.user_configuration_id = uc.user_configuration_id
                SET tfa.status = TRUE
                WHERE uc.user_id = %s
            """, (user_id,))
        else:
            cur.execute("""
                UPDATE two_factor_auth AS tfa
                JOIN user_configuration AS uc ON tfa.user_configuration_id = uc.user_configuration_id
                SET tfa.status = FALSE
                WHERE uc.user_id = %s
            """, (user_id,))

        db.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        cur.close()
