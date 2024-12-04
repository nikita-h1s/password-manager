from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from .db import get_db
from .utils import retrieve_vaults, get_resources_by_vault, encrypt_password

main = Blueprint('main', __name__)


# @main.route('/')
# @main.route('/home')
# def home():
#     return render_template('layout.html')


@main.route('/resource/new', methods=['GET', 'POST'])
def add_resource():
    vault_list = retrieve_vaults()
    if request.method == 'POST':
        resource_details = request.form
        resource = resource_details.get('name')
        password = resource_details.get('password')
        url = resource_details.get('url')
        vault_id = resource_details.get('vault-id')

        if resource and password and vault_id:
            db = get_db()
            cur = db.cursor()
            encrypted_password = encrypt_password(password)
            try:
                cur.execute("INSERT INTO resource (resource_name, resource_url, creation_date) VALUES (%s, %s, NOW())",
                            (resource, url))
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


@main.route('/password-list/', defaults={'vault_id': None, 'resource_id': None})
@main.route('/password-list/resource/<int:resource_id>', defaults={'vault_id': None})
@main.route('/password-list/vault/<int:vault_id>', defaults={'resource_id': None})
@main.route('/password-list/vault/<int:vault_id>/resource/<int:resource_id>')
def view_password_list(vault_id, resource_id):
    # Fetch resources based on the provided vault_id
    if vault_id is not None:
        resource_list = get_resources_by_vault(vault_id)
    else:
        resource_list = get_resources_by_vault()

    vault_list = retrieve_vaults()

    selected_resource_id = None
    if resource_id:
        db = get_db()
        cur = db.cursor()
        query = """SELECT resource.resource_id
                           FROM resource
                           WHERE resource.resource_id = %s"""
        cur.execute(query, (resource_id,))
        result = cur.fetchone()
        if result:
            selected_resource_id = result[0]

    return render_template(
        'passwords_list.html',
        resources=resource_list,
        vaults=vault_list,
        selected_resource_id=selected_resource_id
    )


@main.route('/vault/new', methods=['GET', 'POST'])
def add_vault():
    vault_list = retrieve_vaults()
    if request.method == 'POST':
        vault_details = request.form
        vault = vault_details.get('vault-name')
        description = vault_details.get('vault-description')

        if vault:
            db = get_db()
            cur = db.cursor()
            try:
                cur.execute("INSERT INTO vault (vault_name, vault_description) VALUES (%s, %s)", (vault, description))
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
def view_vaults():
    vault_list = retrieve_vaults()

    return render_template('layout.html', vaults=vault_list)


@main.route('/password-list/', defaults={'vault_id': None, 'resource_id': None}, methods=['POST'])
@main.route('/password-list/resource/<int:resource_id>', defaults={'vault_id': None}, methods=['POST'])
@main.route('/password-list/vault/<int:vault_id>', defaults={'resource_id': None}, methods=['POST'])
@main.route('/password-list/vault/<int:vault_id>/resource/<int:resource_id>', methods=['POST'])
def manage_resource(resource_id=None, vault_id=None):
    db = get_db()
    cur = db.cursor()

    if not resource_id:
        resource_id = request.form.get('resource-id')

    if request.form['action'] == 'update':
        if request.method == 'POST':
            resource_details = request.form
            resource_id = resource_details.get('resource-id')
            resource_name = resource_details.get('name')
            resource_url = resource_details.get('url')
            resource_password = resource_details.get('password')
            cur.execute("SELECT * FROM resource WHERE resource_id = %s", (resource_id,))
            resource = cur.fetchone()
            if resource:
                encrypted_password = encrypt_password(resource_password)
                sql_query_resource = """UPDATE resource
                               SET resource_name = %s,
                                   resource_url = %s 
                               WHERE resource_id = %s"""
                resource_params = (resource_name, resource_url, resource_id)

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
