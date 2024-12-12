import os
from cryptography.fernet import Fernet
from .db import get_db
import string


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


def check_common_password(password):
    # TODO: make a relative path
    with open(r'D:\Programming\nure\pass-manager\passm\data\common-password.txt', 'r') as f:
        common = f.read().splitlines()

    if password in common:
        return True

    return False


def password_strength(password):
    score = 0
    length = len(password)

    upper_case = any(c.isupper() for c in password)
    lower_case = any(c.islower() for c in password)
    special = any(c in string.punctuation for c in password)
    digits = any(c.isdigit() for c in password)

    characters = [upper_case, lower_case, special, digits]

    if length > 8:
        score += 1
    if length > 12:
        score += 1
    if length > 17:
        score += 1
    if length > 20:
        score += 1

    score += sum(characters) - 1

    if score < 4:
        return 'Weak', score
    elif score == 4:
        return 'Okay', score
    elif 4 < score < 6:
        return 'Good', score
    else:
        return 'Strong', score


def get_password_stats():
    """Returns arrays of weak & repeated passwords"""
    # Fetching a list of passwords
    db = get_db()
    cur = db.cursor()

    sql_query = """SELECT password_id, encrypted_password FROM password"""
    cur.execute(sql_query)
    password_list = cur.fetchall()

    # Looking for weak passwords
    weak_password_list = []
    for idx, p in password_list:
        decrypted_password = decrypt_password(p)
        if check_common_password(decrypted_password):
            weak_password_list.append(idx)

        strength, score = password_strength(decrypted_password)

        if score <= 4:
            weak_password_list.append(idx)

    # Looking for repeated passwords
    password_groups = {}
    for idx, p in password_list:
        decrypted_password = decrypt_password(p)
        if decrypted_password in password_groups:
            password_groups[decrypted_password].append(idx)
        else:
            password_groups[decrypted_password] = [idx]

    repeated_password_list = [group for group in password_groups.values() if len(group) > 1]

    return weak_password_list, repeated_password_list
