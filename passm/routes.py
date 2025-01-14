import csv
import io
import json
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, session

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
    cur = db.cursor()

    selected_resource_id = None
    vault_name = None
    if resource_id:
        query = """SELECT resource.resource_id
                           FROM resource
                           WHERE resource.resource_id = %s"""
        cur.execute(query, (resource_id,))
        result = cur.fetchone()
        cur.close()
        if result:
            selected_resource_id = result[0]

    # Fetch resources based on the provided vault_id
    if vault_id is not None:
        resource_list = get_resources_by_vault(vault_id)
        db = get_db()
        cur = db.cursor()
        vault_name_query = "SELECT vault_name FROM vault WHERE vault_id = %s"
        cur.execute(vault_name_query, (vault_id,))
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
        vault_name=vault_name
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
    db = get_db()
    cur = db.cursor(dictionary=True)

    # Fetch export logs
    cur.execute("""
            SELECT file_type, num_of_exported_resources, user_id, export_date
            FROM resources_export
            WHERE user_id = %s
            ORDER BY export_date DESC
            LIMIT 10;
        """, (session.get('user_id'),))
    log_data = cur.fetchall()
    print(log_data)

    if request.method == 'GET':
        return render_template('export.html', log_data=log_data)

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
