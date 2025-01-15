import csv
import io
import json
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, session, jsonify

from .db import get_db
from .utils import (retrieve_vaults, get_resources_by_vault, encrypt_password, decrypt_password,
                    get_password_stats, login_required)

main = Blueprint('main', __name__)


@main.route('/resource/new', methods=['GET', 'POST'])
@login_required
def add_resource():
    vault_list = retrieve_vaults()
    if request.method == 'POST':
        resource_details = request.form
        resource = resource_details.get('name')
        username = resource_details.get('username')
        email = resource_details.get('email')
        password = resource_details.get('password')
        url = resource_details.get('url')
        vault_id = resource_details.get('vault-id')

        if resource and password and vault_id and email:
            db = get_db()
            cur = db.cursor()
            encrypted_password = encrypt_password(password)
            try:
                cur.execute("INSERT INTO resource (resource_name, resource_username,"
                            "resource_email, resource_url, creation_date)"
                            "VALUES (%s, %s, %s, %s, NOW())",
                            (resource, username, email, url))
                resource_id = cur.lastrowid

                cur.execute("""INSERT INTO password (encrypted_password, resource_id, 
                               creation_date, last_modified_date) 
                               VALUES (%s, %s, NOW(), NOW())""",
                            (encrypted_password, resource_id))

                cur.execute("INSERT INTO resource_vault (resource_id, vault_id) VALUES (%s, %s)",
                            (resource_id, vault_id))
                db.commit()
                flash('Resource added successfully', 'info')

                return redirect(url_for('main.add_resource'))
            except Exception as e:
                db.rollback()
                print("An error occurred:", e)
                flash('Failed to add resource', 'danger')
            finally:
                cur.close()
        else:
            flash('Please fill out all fields', 'danger')

    return render_template('add_resource.html', vaults=vault_list)


@main.route('/', defaults={'vault_id': None, 'resource_id': None})
@main.route('/password-list/', defaults={'vault_id': None, 'resource_id': None})
@main.route('/password-list/resource/<int:resource_id>', defaults={'vault_id': None})
@main.route('/password-list/vault/<int:vault_id>', defaults={'resource_id': None})
@main.route('/password-list/vault/<int:vault_id>/resource/<int:resource_id>')
@login_required
def view_password_list(vault_id, resource_id):
    # TODO: make a global cursor for not recreating same variables
    db = get_db()
    cur = db.cursor(dictionary=True)

    user_id = session.get('user_id')

    cur.execute("""
            SELECT u.username, u.email, uc.automatic_logout_time, uc.show_passwords_by_default
            FROM user u
            JOIN user_configuration uc ON u.id = uc.user_id
            WHERE u.id = %s
        """, (user_id,))
    user = cur.fetchone()
    cur.close()

    db = get_db()
    cur = db.cursor()

    selected_resource_id = None
    vault_name = None
    if resource_id:
        query = """SELECT resource.resource_id
                           FROM resource
                           INNER JOIN resource_vault ON resource.resource_id = resource_vault.resource_id
                           INNER JOIN vault ON vault.vault_id = resource_vault.vault_id
                           WHERE vault.user_id = %s AND resource.resource_id = %s"""
        cur.execute(query, (user_id, resource_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            selected_resource_id = result[0]

    # Fetch resources based on the provided vault_id
    if vault_id is not None:
        resource_list = get_resources_by_vault(vault_id)
        db = get_db()
        cur = db.cursor()
        vault_name_query = "SELECT vault_name FROM vault WHERE vault_id = %s AND vault.user_id = %s"
        cur.execute(vault_name_query, (vault_id, user_id,))
        vault_name_result = cur.fetchone()
        if vault_name_result:
            vault_name = vault_name_result[0]  # Get the vault name
    else:
        resource_list = get_resources_by_vault()

    vault_list = retrieve_vaults()

    return render_template(
        'passwords_list.html',
        resources=resource_list,
        vaults=vault_list,
        selected_resource_id=selected_resource_id,
        vault_name=vault_name,
        user=user
    )


@main.route('/vault/new', methods=['GET', 'POST'])
@login_required
def add_vault():
    vault_list = retrieve_vaults()
    if request.method == 'POST':
        vault_details = request.form
        vault = vault_details.get('vault-name')
        description = vault_details.get('vault-description')

        if vault:
            db = get_db()
            cur = db.cursor()
            user_id = session.get('user_id')
            try:
                cur.execute("INSERT INTO vault (vault_name, vault_description, user_id) VALUES (%s, %s, %s)",
                            (vault, description, user_id))
                db.commit()
                flash('Vault added successfully', 'info')
                return redirect(url_for('main.add_vault'))
            except Exception as e:
                db.rollback()
                print("An error occurred:", e)
                flash('Failed to add vault', 'danger')
            finally:
                cur.close()

    return render_template('add_vault.html', vaults=vault_list)


@main.route('/')
@main.route('/home')
@login_required
def view_vaults():
    vault_list = retrieve_vaults()

    return render_template('layout.html', vaults=vault_list)


@main.route('/password-list/', defaults={'vault_id': None, 'resource_id': None}, methods=['POST'])
@main.route('/password-list/resource/<int:resource_id>', defaults={'vault_id': None}, methods=['POST'])
@main.route('/password-list/vault/<int:vault_id>', defaults={'resource_id': None}, methods=['POST'])
@main.route('/password-list/vault/<int:vault_id>/resource/<int:resource_id>', methods=['POST'])
@login_required
def manage_resource(resource_id=None, vault_id=None):
    db = get_db()
    cur = db.cursor(dictionary=True)

    if not resource_id:
        resource_id = request.form.get('resource-id')

    if request.form['action'] == 'update':
        if request.method == 'POST':
            resource_details = request.form
            resource_id = resource_details.get('resource-id')
            resource_name = resource_details.get('name')
            resource_username = resource_details.get('username')
            resource_email = resource_details.get('email')
            resource_url = resource_details.get('url')
            resource_password = resource_details.get('password')

            cur.execute("SELECT * FROM resource WHERE resource_id = %s", (resource_id,))
            resource = cur.fetchone()
            cur.execute("SELECT * FROM password WHERE resource_id = %s", (resource_id,))
            password = cur.fetchone()

            if resource and password:
                encrypted_password = encrypt_password(resource_password)

                # Add old password to password_history table
                cur.execute(
                    """INSERT INTO password_history (password_id, old_encrypted_password)
                       VALUES (%s, %s)""",
                    (password['password_id'], password['encrypted_password'])
                )

                sql_query_resource = """UPDATE resource
                               SET resource_name = %s,
                                   resource.resource_url = %s,
                                   resource_username = %s,
                                   resource_email = %s 
                               WHERE resource_id = %s"""
                resource_params = (resource_name, resource_url, resource_username, resource_email, resource_id)

                sql_query_password = """UPDATE password
                                        SET last_modified_date = NOW(),
                                        encrypted_password = %s
                                        WHERE resource_id = %s"""
                password_params = (encrypted_password, resource_id)

                cur.execute(sql_query_resource, resource_params)
                cur.execute(sql_query_password, password_params)
                db.commit()
                flash('Resource updated successfully!', 'success')
            else:
                flash('Resource not found. Update failed.', 'error')
    elif request.form['action'] == 'delete':
        if resource_id:
            query = """DELETE FROM resource WHERE resource_id = %s"""
            cur.execute(query, (resource_id,))
            db.commit()
            flash('Resource deleted successfully!', 'info')
        else:
            flash('Resource not found. Delete failed.', 'danger')

    return redirect(url_for('main.view_password_list'))


@main.route('/pass-monitor/')
@login_required
def view_password_statistics():
    vault_list = retrieve_vaults()
    (weak_password_list, okay_password_list, good_password_list,
     strong_password_list, repeated_password_list) = get_password_stats()

    return render_template('pass_monitor.html', vaults=vault_list,
                           weak_password_list=weak_password_list,
                           okay_password_list=okay_password_list,
                           good_password_list=good_password_list,
                           strong_password_list=strong_password_list,
                           repeated_password_list=repeated_password_list)


@main.route('/export/resources/', methods=['GET', 'POST'])
@login_required
def export_resources():
    vault_list = retrieve_vaults()
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Fetch export logs
    cur.execute("""
            SELECT file_type, num_of_exported_resources, user_id, export_date
            FROM resources_export
            WHERE user_id = %s
            ORDER BY export_date DESC;
        """, (session.get('user_id'),))
    log_data = cur.fetchall()
    print(log_data)

    if request.method == 'GET':
        return render_template('export.html', log_data=log_data, vaults=vault_list)

    file_format = request.form.get('format', 'csv')

    query = """
    SELECT resource.resource_name, resource.resource_email, resource.resource_username, resource.resource_url,
           resource.creation_date, password.encrypted_password
    FROM resource
    INNER JOIN password ON resource.resource_id = password.resource_id
    INNER JOIN resource_vault ON resource.resource_id = resource_vault.resource_id
    INNER JOIN vault ON vault.vault_id = resource_vault.vault_id
    WHERE vault.user_id = %s;
    """
    cur.execute(query, (session.get('user_id'),))
    resources = cur.fetchall()

    if len(resources) <= 0:
        flash('No resources found to export', 'danger')
        return render_template('export.html')

    for resource in resources:
        encrypted_password = resource.pop("encrypted_password", None)  # Remove encrypted_password from the dictionary
        if encrypted_password:
            try:
                resource["password"] = decrypt_password(encrypted_password)  # Add decrypted value as "password"
            except Exception as e:
                resource["password"] = f"Error: {str(e)}"

    def log_data():
        # Log export metadata in the database
        try:
            cur.execute("""
                            INSERT INTO resources_export (file_type, num_of_exported_resources, user_id)
                            VALUES (%s, %s, %s);
                        """, (file_format, len(resources), session['user_id']))
            db.commit()
        except Exception as e:
            db.rollback()
            flash(f"Error logging export metadata: {str(e)}", 'danger')
            return render_template('export.html')

    if file_format == 'csv':
        # Generate CSV file
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=resources[0].keys())

        writer.writeheader()
        writer.writerows(resources)

        footer_row = {key: '' for key in resources[0].keys()}
        fieldnames = list(resources[0].keys())

        if len(fieldnames) >= 2:
            footer_row[fieldnames[0]] = 'File Created On'
            footer_row[fieldnames[1]] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        writer.writerow(footer_row)

        output.seek(0)

        log_data()

        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment;filename=resources.csv'}
        )

    elif file_format == 'json':
        for resource in resources:
            for key, value in resource.items():
                if isinstance(value, datetime):
                    resource[key] = value.isoformat()

        log_data()

        # Generate JSON file
        return Response(
            json.dumps(resources),
            mimetype='application/json',
            headers={'Content-Disposition': 'attachment;filename=resources.json'}
        )

    # If format is invalid, return an error response
    return "Invalid format selected", 400


@main.route('/api/password-history/', methods=['GET'])
@main.route('/api/password-history/<int:resource_id>', methods=['GET'])
def get_password_history(resource_id):
    if not resource_id:
        return jsonify({"error": "Resource ID is required"}), 400

    db = get_db()
    cursor = db.cursor()
    query = """
        SELECT old_encrypted_password, changed_at
        FROM password_history
        WHERE password_id = %s
        ORDER BY changed_at DESC
    """
    cursor.execute(query, (resource_id,))
    history = cursor.fetchall()
    cursor.close()

    if not history:
        return jsonify({"message": "No password history found for the provided resource ID"}), 404

    return jsonify([
        {
            "old_encrypted_password": decrypt_password(row[0]),
            "changed_at": row[1].strftime("%Y-%m-%d %H:%M:%S"),
        }
        for row in history
    ])


@main.route('/account/settings', methods=['GET', 'POST'])
@login_required
def account_settings():
    vault_list = retrieve_vaults()
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.username, u.email, 
               uc.automatic_logout_time, uc.show_passwords_by_default, 
               tfa.status AS status_2fa
        FROM user AS u
        JOIN user_configuration AS uc ON u.id = uc.user_id
        JOIN two_factor_auth AS tfa ON uc.user_configuration_id = tfa.user_configuration_id
        WHERE u.id = %s
    """, (user_id,))

    user = cursor.fetchone()

    username = user['username']
    email = user['email']
    status_2fa = user['status_2fa']

    print(f"Username: {username}, Email: {email}, 2FA Status: {status_2fa}")

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for('auth.login'))

    return render_template('account_settings.html', user=user, vaults=vault_list)


@main.route('/api/user', methods=['PUT'])
@login_required
def update_user():
    if 'user_id' not in session:
        flash("User not found.", "danger")
        return jsonify({"error": "User session is not initialized"}), 401

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        automatic_logout_time = data.get('automatic_logout_time')
        show_passwords_by_default = data.get('show_passwords_by_default')

        if not username or not email:
            flash("Invalid input. Please provide both username and email.", "danger")
            return jsonify({"error": "Invalid input"}), 400

        if automatic_logout_time not in [30, 60, 360, 1440]:
            flash("Invalid automatic logout time.", "danger")
            return jsonify({"error": "Invalid automatic logout time"}), 400

        if not isinstance(show_passwords_by_default, bool):
            flash("Invalid value for show passwords by default.", "danger")
            return jsonify({"error": "Invalid value for show passwords by default"}), 400

        # Check if the email is already in use by another user

        cursor.execute("""
            SELECT id FROM user WHERE email = %s AND id != %s
        """, (email, session['user_id']))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("The email is already associated with another account.", "danger")
            return jsonify({"error": "Email already in use"}), 409

        # Perform database updates
        cursor.execute("""
            UPDATE user
            SET username = %s, email = %s
            WHERE id = %s
        """, (username, email, session['user_id']))

        cursor.execute("""
            UPDATE user_configuration
            SET automatic_logout_time = %s,
                show_passwords_by_default = %s
            WHERE user_id = %s
        """, (automatic_logout_time, show_passwords_by_default, session['user_id']))

        db.commit()

        # Update session data
        session['username'] = username
        session['email'] = email

        flash("Your profile has been updated successfully.", "success")
        return jsonify({"message": "User data updated successfully"}), 200
    except Exception as e:
        # Log the error for debugging
        import traceback
        traceback.print_exc()

        db.rollback()
        flash("An error occurred while updating your profile. Please try again.", "danger")
        return jsonify({"error": str(e)}), 500
