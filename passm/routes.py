from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import get_db

main = Blueprint('main', __name__)


@main.route('/')
@main.route('/home')
def home():
    return render_template('passwords_list.html')


@main.route('/resource/new', methods=['GET', 'POST'])
def add_resource():
    if request.method == 'POST':
        resource_details = request.form
        resource = resource_details.get('name')
        password = resource_details.get('password')

        if resource and password:
            db = get_db()
            cur = db.cursor()
            try:
                cur.execute("INSERT INTO resource (resource_name) VALUES (%s)", (resource,))
                resource_id = cur.lastrowid

                cur.execute("INSERT INTO password (encrypted_password, resource_id) VALUES (%s, %s)",
                            (password, resource_id))
                db.commit()
                flash('Resource added successfully', 'info')

                return redirect(url_for('main.add_resource'))
            except Exception as e:
                db.rollback()
                print("An error occurred:", e)
                flash('Failed to add resource', 'danger')
            finally:
                cur.close()
        elif not resource or not password:
            flash('Please fill out all fields', 'danger')

    return render_template('add_resource.html')


@main.route('/password-list')
def view_passwords():
    db = get_db()
    cur = db.cursor()
    sql_query = """SELECT resource.resource_name, password.encrypted_password FROM resource
                   INNER JOIN password
                   ON password.resource_id = resource.resource_id;"""
    cur.execute(sql_query)
    resources = cur.fetchall()
    cur.close()
    db.close()

    resource_list = []
    for resource in resources:
        resource_dict = {
            'name': resource[0],
            'password': resource[1]
        }
        resource_list.append(resource_dict)

    return render_template('passwords_list.html', resources=resource_list)


@main.route('/vault/new', methods=['GET', 'POST'])
def add_vault():
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

    return render_template('add_vault.html')
