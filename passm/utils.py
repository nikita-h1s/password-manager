from .db import get_db

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
