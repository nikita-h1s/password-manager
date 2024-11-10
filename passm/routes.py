from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import get_db

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
        vault_id = resource_details.get('vault-id')

        if resource and password and vault_id:
            db = get_db()
            cur = db.cursor()
            try:
                cur.execute("INSERT INTO resource (resource_name) VALUES (%s)", (resource,))
                resource_id = cur.lastrowid

                cur.execute("INSERT INTO password (encrypted_password, resource_id) VALUES (%s, %s)",
                            (password, resource_id))

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
        elif not resource or not password:
            flash('Please fill out all fields', 'danger')

    return render_template('add_resource.html', vaults=vault_list)


@main.route('/password-list')
def view_all_passwords():
    resource_list = get_resources_by_vault()
    return render_template('passwords_list.html', resources=resource_list)


@main.route('/password-list/<int:vault_id>')
def view_vault_passwords(vault_id):
    resource_list = get_resources_by_vault(vault_id)
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


@main.route('/')
@main.route('/home')
def view_vaults():
    vault_list = retrieve_vaults()

    return render_template('layout.html', vaults=vault_list)


def retrieve_vaults():
    """Returns a list of vaults"""
    db = get_db()
    cur = db.cursor()
    sql_query = "SELECT vault.vault_id, vault.vault_name, vault.vault_description FROM vault;"
    cur.execute(sql_query)
    vaults = cur.fetchall()
    cur.close()
    db.close()

    vault_list = []
    for vault in vaults:
        vault_dict = {
            'id': vault[0],
            'name': vault[1],
            'description': vault[2]
        }
        vault_list.append(vault_dict)

    return vault_list


def get_resources_by_vault(vault_id=None):
    db = get_db()
    cur = db.cursor()
    if vault_id:
        sql_query = """
                SELECT resource.resource_name, password.encrypted_password 
                FROM resource
                INNER JOIN password ON password.resource_id = resource.resource_id
                INNER JOIN resource_vault ON resource.resource_id = resource_vault.resource_id
                WHERE resource_vault.vault_id = %s;
            """
        cur.execute(sql_query, (vault_id,))
    else:
        sql_query = """SELECT resource.resource_name, password.encrypted_password FROM resource
                           INNER JOIN password
                           ON password.resource_id = resource.resource_id;"""
        cur.execute(sql_query)

    resources = cur.fetchall()
    cur.close()
    db.close()

    return [{'name': resource[0], 'password': resource[1]} for resource in resources]
