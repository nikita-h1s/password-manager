import os

import requests
from flask import url_for, current_app, session, redirect, flash
from functools import wraps
from urllib.parse import urlparse
from cryptography.fernet import Fernet
from .db import get_db
import string


def retrieve_vaults():
    """Returns a list of vaults"""
    db = get_db()
    cur = db.cursor()
    user_id = session.get('user_id')
    sql_query = (f"SELECT vault.vault_id, vault.vault_name, vault.vault_description "
                 f"FROM vault WHERE user_id = {user_id};")
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
                SELECT resource.resource_id, resource.resource_name, resource.resource_username,
                       resource.resource_email, password.encrypted_password,
                       resource.creation_date, resource.resource_url, password.last_modified_date 
                FROM resource
                INNER JOIN password ON password.resource_id = resource.resource_id
                INNER JOIN resource_vault ON resource.resource_id = resource_vault.resource_id
                WHERE resource_vault.vault_id = %s;
            """
        cur.execute(sql_query, (vault_id,))
    else:
        sql_query = """SELECT resource.resource_id, resource.resource_name, resource.resource_username,
                              resource.resource_email, password.encrypted_password,
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
        resource_creation_date = resource[5].strftime('%d %b %Y, %H:%M')
        pass_last_modified_date = resource[7].strftime('%d %b %Y, %H:%M')
        resource_url = resource[6]
        resource_favicon = get_favicon_url(resource_url)
        resource_list[resource_id] = {'name': resource[1], 'username': resource[2],
                                      'email': resource[3], 'password': decrypt_password(resource[4]),
                                      'resource_creation_date': resource_creation_date, 'resource_url': resource_url,
                                      'pass_last_modified_date': pass_last_modified_date,
                                      'resource_favicon': resource_favicon}

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
    base_dir = os.path.dirname(os.path.abspath(__file__))

    file_path = os.path.join(base_dir, 'data', 'common-password.txt')

    with open(file_path, 'r') as f:
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
    """Returns arrays of repeated & different types of weak passwords"""
    # Fetching a list of passwords
    db = get_db()
    cur = db.cursor()

    sql_query = """SELECT password_id, encrypted_password FROM password"""
    cur.execute(sql_query)
    password_list = cur.fetchall()

    # Looking for weak passwords
    weak_password_ids = []
    okay_password_ids = []
    good_password_ids = []
    strong_password_ids = []
    for idx, p in password_list:
        decrypted_password = decrypt_password(p)
        if check_common_password(decrypted_password):
            weak_password_ids.append(idx)

        strength, score = password_strength(decrypted_password)

        if score < 4:
            weak_password_ids.append(idx)
        elif score == 4:
            okay_password_ids.append(idx)
        elif 4 < score < 6:
            good_password_ids.append(idx)
        elif score >= 6:
            strong_password_ids.append(idx)

    # Looking for repeated passwords
    password_groups = {}
    for idx, p in password_list:
        decrypted_password = decrypt_password(p)
        if decrypted_password in password_groups:
            password_groups[decrypted_password].append(idx)
        else:
            password_groups[decrypted_password] = [idx]

    res = [group for group in password_groups.values() if len(group) > 1]
    repeated_password_ids = [item for sublist in res for item in sublist]

    def fetch_password_details(ids):
        if not ids:
            return []

        placeholders = ', '.join(['%s'] * len(ids))
        query = f"""SELECT resource.resource_name, password.encrypted_password 
                    FROM password 
                    INNER JOIN resource ON password.resource_id = resource.resource_id 
                    WHERE resource.resource_id IN ({placeholders});"""
        cur.execute(query, tuple(ids))
        result = cur.fetchall()
        pass_list = [(p[0], decrypt_password(str(p[1]))) for p in result]
        return pass_list

    weak_password_list = fetch_password_details(weak_password_ids)
    repeated_password_list = fetch_password_details(repeated_password_ids)
    okay_password_list = fetch_password_details(okay_password_ids)
    good_password_list = fetch_password_details(good_password_ids)
    strong_password_list = fetch_password_details(strong_password_ids)

    return (weak_password_list, okay_password_list, good_password_list,
            strong_password_list, repeated_password_list)


def get_favicon_url(domain_url):
    """Fetch and cache favicon for a domain."""
    FAVICON_CACHE_DIR = os.path.join(current_app.root_path, 'static', 'icons', 'favicons')

    if not os.path.exists(FAVICON_CACHE_DIR):
        os.makedirs(FAVICON_CACHE_DIR)

    try:
        # Parse the domain
        parsed_url = urlparse(domain_url)
        domain_name = parsed_url.netloc.split(':')[0]
        if not domain_name:
            return url_for('static', filename='icons/default_resource_icon.svg')

        # Build favicon cache path
        filename = f"{domain_name}.png"
        filepath = os.path.join(FAVICON_CACHE_DIR, filename)

        # Check if favicon is already cached
        if not os.path.exists(filepath):
            favicon_url = f"https://www.google.com/s2/favicons?sz=32&domain_url={domain_name}"
            response = requests.get(favicon_url, timeout=5)

            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
            else:
                return url_for('static', filename='icons/default_resource_icon.svg')

        # Return cached favicon URL
        return url_for('static', filename=f'icons/favicons/{filename}')

    except (requests.RequestException, ValueError) as e:
        print(f"Error fetching favicon: {e}")
        return url_for('static', filename='icons/default_resource_icon.svg')


def login_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to login first!', 'warning')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)

    return decorated_view
