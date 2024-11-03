import mysql.connector
from flask import current_app, g


def get_db():
    """Get a MySQL database connection."""
    if 'db' not in g or not g.db.is_connected():
        g.db = mysql.connector.connect(
            host=current_app.config['MYSQL_HOST'],
            user=current_app.config['MYSQL_USER'],
            password=current_app.config['MYSQL_PASSWORD'],
            database=current_app.config['MYSQL_DB']
        )

    return g.db


def close_db(e=None):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_app(app):
    """Initialize the app with the MySQL database."""
    app.teardown_appcontext(close_db)
