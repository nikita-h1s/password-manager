import os
from cryptography.fernet import Fernet
from .db import get_db
from datetime import datetime


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
                SELECT resource.resource_id, resource.resource_name, password.encrypted_password,
                       resource.creation_date, resource.resource_url, password.last_modified_date 
                FROM resource
                INNER JOIN password ON password.resource_id = resource.resource_id
                INNER JOIN resource_vault ON resource.resource_id = resource_vault.resource_id
                WHERE resource_vault.vault_id = %s;
            """
        cur.execute(sql_query, (vault_id,))
    else:
        sql_query = """SELECT resource.resource_id, resource.resource_name, password.encrypted_password,
                              resource.creation_date, resource.resource_url, password.last_modified_date 
                       FROM resource
                       INNER JOIN password
                       ON password.resource_id = resource.resource_id;"""
        cur.execute(sql_query)

    resources = cur.fetchall()
    cur.close()
    db.close()

    resource_list = {}
    for resource in resources:
        resource_id = resource[0]
        resource_creation_date = resource[3].strftime('%d %b %Y, %H:%M')
        pass_last_modified_date = resource[5].strftime('%d %b %Y, %H:%M')
        resource_list[resource_id] = {'name': resource[1], 'password': decrypt_password(resource[2]),
                                      'resource_creation_date': resource_creation_date, 'resource_url': resource[4],
                                      'pass_last_modified_date': pass_last_modified_date}

    return resource_list

def encrypt_password(password):
    crypter = Fernet(os.environ.get('ENCRYPTION_KEY'))
    encrypted_password = crypter.encrypt(password.encode('utf-8'))
    return encrypted_password


def decrypt_password(encrypted_password):
    crypter = Fernet(os.environ.get('ENCRYPTION_KEY'))
    decrypted_password = crypter.decrypt(encrypted_password)
    return decrypted_password.decode('utf-8')
