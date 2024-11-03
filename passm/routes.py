from flask import Blueprint, render_template, request, redirect, url_for, flash
from .db import get_db

main = Blueprint('main', __name__)


@main.route('/', methods=['GET', 'POST'])
@main.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        resource_details = request.form
        resource = resource_details.get('name')
        password = resource_details.get('password')

        if resource and password:
            db = get_db()
            cur = db.cursor()
            try:
                cur.execute("INSERT INTO resource (resource_name) VALUES (%s)", (resource,))
                cur.execute("INSERT INTO password (encrypted_password) VALUES (%s)", (password,))
                db.commit()
                flash('Data added successfully', 'info')
            except Exception as e:
                db.rollback()
                print("An error occurred:", e)
                flash('Failed to add data', 'danger')
            finally:
                cur.close()

            return redirect(url_for('main.home'))
    return render_template('layout.html')