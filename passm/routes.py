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


@main.route('/password-list')
def view_all_passwords():
    resource_list = get_resources_by_vault()
    vault_list = retrieve_vaults()
    return render_template('passwords_list.html', resources=resource_list, vaults=vault_list)


@main.route('/password-list/<int:vault_id>')
def view_vault_passwords(vault_id):
    resource_list = get_resources_by_vault(vault_id)
    vault_list = retrieve_vaults()
    return render_template('passwords_list.html', resources=resource_list, vaults=vault_list)


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


@main.route('/update-resource', methods=['POST'])
def update_resource():
    db = get_db()
    cur = db.cursor()

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
                           SET resource_url = %s 
                           WHERE resource_id = %s"""
            resource_params = (resource_url, resource_id)

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

    return redirect(url_for('main.view_all_passwords'))
