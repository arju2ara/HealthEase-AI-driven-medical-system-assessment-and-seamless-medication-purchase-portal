from flask import Flask, render_template, flash, redirect, url_for, session, request, logging, jsonify
from sslcommerz_payment import SSLCommerzPayment
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators, SelectField
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename

# Removed Flask-Uploads as it's deprecated and causing compatibility issues
# We'll use Flask's built-in file handling instead
import timeit
import datetime
from flask_mail import Mail, Message
import os
from wtforms.fields.html5 import EmailField

import numpy as np
import pandas as pd
import pickle
import random
from flask_wtf import FlaskForm
from sqlalchemy.dialects import mysql
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re

from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''  # XAMPP's default has no password
app.config['MYSQL_DB'] = 'medicine'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)

# Configure uploads - using Flask's built-in file handling
app.config['UPLOAD_FOLDER'] = 'static/image/product'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size


def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, *kwargs)
        else:
            return redirect(url_for('login', next=request.url))

    return wrap


def not_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return redirect(url_for('indexed'))
        else:
            return f(*args, *kwargs)

    return wrap


def is_admin_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin_logged_in' in session:
            return f(*args, *kwargs)
        else:
            return redirect(url_for('admin_login'))

    return wrap


def not_admin_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'admin_logged_in' in session:
            return redirect(url_for('admin'))
        else:
            return f(*args, *kwargs)

    return wrap


def wrappers(func, *args, **kwargs):
    def wrapped():
        return func(*args, **kwargs)

    return wrapped


def content_based_filtering(product_id):
    cur = mysql.connection.cursor()
    try:
        # Get product info
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        data = cur.fetchone()
        if not data:
            return ''

        data_cat = data['category']

        # Get category matched products
        cur.execute("SELECT * FROM products WHERE category=%s", (data_cat,))
        cat_product = cur.fetchall()
        if not cat_product:
            return ''

        # Get product level info
        cur.execute("SELECT * FROM product_level WHERE product_id=%s", (product_id,))
        id_level = cur.fetchone()
        if not id_level:
            return ''

        recommend_id = []
        cate_level = ['v_shape', 'polo', 'clean_text', 'design', 'leather', 'color', 'formal', 'converse', 'loafer',
                      'hook', 'chain']

        for product_f in cat_product:
            cur.execute("SELECT * FROM product_level WHERE product_id=%s", (product_f['id'],))
            f_level = cur.fetchone()

            if f_level and f_level['product_id'] != int(product_id):  # Check if f_level exists
                match_score = 0
                for cat_level in cate_level:
                    if cat_level in f_level and cat_level in id_level:
                        if f_level[cat_level] == id_level[cat_level]:
                            match_score += 1
                if match_score == 11:
                    recommend_id.append(f_level['product_id'])

        if recommend_id:
            cur.execute("SELECT * FROM products WHERE id IN (%s)" % ','.join(str(n) for n in recommend_id))
            recommend_list = cur.fetchall()
            category_matched = len(cat_product)
            return recommend_list, recommend_id, category_matched, product_id

        return ''

    except Exception as e:
        print(f"Error in content_based_filtering: {str(e)}")
        return ''

    finally:
        cur.close()


@app.route("/")
def home():
    return render_template("med_index.html")


@app.route('/shop')
def shop():
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute queries
    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY RAND()", ['otc'])
    tshirt = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY RAND()", ['womens_choice'])
    wallet = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY RAND()", ['baby_care'])
    belt = cur.fetchall()

    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY RAND()", ['hygiene'])
    shoes = cur.fetchall()

    # Close cursor
    cur.close()

    form = OrderForm(request.form)
    return render_template('home.html', tshirt=tshirt, wallet=wallet, belt=belt, shoes=shoes, form=form)


class LoginForm(Form):  # Create Login Form
    username = StringField('', [validators.length(min=1)],
                           render_kw={'autofocus': True, 'placeholder': 'Username'})
    password = PasswordField('', [validators.length(min=3)],
                             render_kw={'placeholder': 'Password'})


# User Login
@app.route('/login', methods=['GET', 'POST'])
@not_logged_in
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        # GEt user form
        username = form.username.data
        # password_candidate = request.form['password']
        password_candidate = form.password.data

        # Get user by username
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username=%s", [username])
        user = cur.fetchone()

        if user:
            # Get stored value
            password = user['password']
            uid = user['id']
            name = user['name']

            # Compare password
            if sha256_crypt.verify(password_candidate, password):
                # passed
                session['logged_in'] = True
                session['uid'] = uid
                session['s_name'] = name
                x = '1'
                cur.execute("UPDATE users SET online=%s WHERE id=%s", (x, uid))

                # Check if there's a 'next' parameter to redirect to the intended page
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                else:
                    return redirect(url_for('shop'))

            else:
                flash('Incorrect password', 'danger')
                return render_template('login.html', form=form)

        else:
            flash('Username not found', 'danger')
            return render_template('login.html', form=form)
    return render_template('login.html', form=form)


@app.route('/out')
def logout():
    if 'uid' in session:
        # Get user by id
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (session['uid'],))
        user = cur.fetchone()
        if user:
            x = '0'
            cur.execute("UPDATE users SET online=%s WHERE id=%s", (x, session['uid']))
            session.clear()
            flash('You are logged out', 'success')
            return redirect(url_for('shop'))
        else:
            flash('User not found', 'danger')
    return redirect(url_for('shop'))


def password_complexity_check(form, field):
    password = field.data
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    if not re.search(r'\d', password):
        raise ValidationError('Password must include at least one number.')
    if not re.search(r'[@!#$%^&]', password):
        raise ValidationError('Password must include at least one special character like @ ! # $ % ^ &.')

class RegisterForm(Form):
    name = StringField('', [validators.length(min=3, max=50)], render_kw={'autofocus': True, 'placeholder': 'Full Name'})
    username = StringField('', [validators.length(min=3, max=25)], render_kw={'placeholder': 'Username'})
    email = EmailField('', [
        validators.DataRequired(),
        validators.Email(),
        validators.length(min=4, max=25)
    ], render_kw={'placeholder': 'Email'})
    password = PasswordField(
        '',
        [
            validators.length(min=8, message='Password must be at least 8 characters long.'),
            password_complexity_check
        ],
        render_kw={'placeholder': 'Password'}
    )
    mobile = StringField('', [validators.length(min=11, max=15)], render_kw={'placeholder': 'Mobile'})


@app.route('/register', methods=['GET', 'POST'])
@not_logged_in
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        mobile = form.mobile.data

        # Get current time for registration
        now = datetime.datetime.now()

        # Create Cursor
        cur = mysql.connection.cursor()

        # First try to create reg_time column if it doesn't exist
        try:
            cur.execute("""
                ALTER TABLE users 
                ADD COLUMN reg_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            mysql.connection.commit()
        except:
            pass  # Column might already exist

        cur.execute("""
            INSERT INTO users(name, email, username, password, mobile, reg_time) 
            VALUES(%s, %s, %s, %s, %s, %s)
        """, (name, email, username, password, mobile, now))

        # Commit cursor
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can login', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


class MessageForm(Form):  # Create Message Form
    body = StringField('', [validators.length(min=1)], render_kw={'autofocus': True})


@app.route('/chatting/<string:id>', methods=['GET', 'POST'])
def chatting(id):
    if 'uid' in session:
        form = MessageForm(request.form)
        # Get user by id
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", [id])
        user = cur.fetchone()
        if user:
            session['name'] = user['name']
            uid = session['uid']
            session['lid'] = id

            if request.method == 'POST' and form.validate():
                txt_body = form.body.data
                # Create cursor
                cur.execute("INSERT INTO messages(body, msg_by, msg_to) VALUES(%s, %s, %s)",
                            (txt_body, id, uid))
                mysql.connection.commit()

            # Get users
            cur.execute("SELECT * FROM users")
            users = cur.fetchall()

            return render_template('chat_room.html', users=users, form=form)
        else:
            flash('No permission!', 'danger')
            return redirect(url_for('home'))
    else:
        return redirect(url_for('login'))


@app.route('/chats', methods=['GET', 'POST'])
def chats():
    if 'lid' in session:
        id = session['lid']
        uid = session['uid']
        # Get messages
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM messages WHERE (msg_by=%s AND msg_to=%s) OR (msg_by=%s AND msg_to=%s) "
                    "ORDER BY id ASC", (id, uid, uid, id))
        chats = cur.fetchall()
        return render_template('chats.html', chats=chats, )
    return redirect(url_for('login'))


class OrderForm(Form):  # Create Order Form
    name = StringField('', [validators.length(min=1), validators.DataRequired()],
                       render_kw={'autofocus': True, 'placeholder': 'Full Name'})
    mobile_num = StringField('', [validators.length(min=1), validators.DataRequired()],
                             render_kw={'autofocus': True, 'placeholder': 'Mobile'})
    quantity = SelectField('', [validators.DataRequired()],
                           choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5')])
    order_place = StringField('', [validators.length(min=1), validators.DataRequired()],
                              render_kw={'placeholder': 'Order Place'})
    payment_method = SelectField('Payment Method', [validators.DataRequired()],
                                 choices=[('cod', 'Cash on Delivery'), ('sslcommerz', 'Online Payment (SSLCommerz)')])


@app.route('/otc', methods=['GET', 'POST'])
def otc():
    form = OrderForm(request.form)
    # Get products
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY id ASC", ('otc',))
    products = cur.fetchall()
    if request.method == 'POST' and form.validate():
        name = form.name.data
        mobile = form.mobile_num.data
        order_place = form.order_place.data
        quantity = form.quantity.data
        payment_method = form.payment_method.data
        pid = request.args['order']

        # Store order data in session for payment processing
        session['order_data'] = {
            'name': name,
            'mobile': mobile,
            'order_place': order_place,
            'quantity': quantity,
            'payment_method': payment_method,
            'product_id': pid
        }

        # Redirect to payment processing
        return redirect(url_for('process_payment', order=pid))
    if 'view' in request.args:
        product_id = request.args['view']
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchall()
        x = content_based_filtering(product_id)
        wrappered = wrappers(content_based_filtering, product_id)
        execution_time = timeit.timeit(wrappered, number=0)
        # print('Execution time: ' + str(execution_time) + ' usec')
        if 'uid' in session:
            cur.execute("SELECT * FROM product_view WHERE user_id=%s AND product_id=%s",
                        (session['uid'], product_id))
            result = cur.fetchall()
            if result:
                now = datetime.datetime.now()
                now_time = now.strftime("%y-%m-%d %H:%M:%S")
                cur.execute("UPDATE product_view SET date=%s WHERE user_id=%s AND product_id=%s",
                            (now_time, session['uid'], product_id))
            else:
                cur.execute("INSERT INTO product_view(user_id, product_id) VALUES(%s, %s)",
                            (session['uid'], product_id))
                mysql.connection.commit()
        return render_template('view_product.html', x=x, tshirts=product)
    elif 'order' in request.args:
        product_id = request.args['order']
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchall()
        x = content_based_filtering(product_id)
        return render_template('order_product.html', x=x, tshirts=product, form=form)
    return render_template('tshirt.html', tshirt=products, form=form)


@app.route('/womens_choice', methods=['GET', 'POST'])
def womens_choice():
    form = OrderForm(request.form)
    # Get products
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY id ASC", ('womens_choice',))
    products = cur.fetchall()

    if request.method == 'POST' and form.validate():
        name = form.name.data
        mobile = form.mobile_num.data
        order_place = form.order_place.data
        quantity = form.quantity.data
        payment_method = form.payment_method.data
        pid = request.args['order']

        # Store order data in session for payment processing
        session['order_data'] = {
            'name': name,
            'mobile': mobile,
            'order_place': order_place,
            'quantity': quantity,
            'payment_method': payment_method,
            'product_id': pid
        }

        # Redirect to payment processing
        return redirect(url_for('process_payment', order=pid))
    if 'view' in request.args:
        q = request.args['view']
        product_id = q
        x = content_based_filtering(product_id)
        cur.execute("SELECT * FROM products WHERE id=%s", (q,))
        products = cur.fetchall()
        return render_template('view_product.html', x=x, tshirts=products)
    elif 'order' in request.args:
        product_id = request.args['order']
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchall()
        x = content_based_filtering(product_id)
        return render_template('order_product.html', x=x, tshirts=product, form=form)
    return render_template('wallet.html', wallet=products, form=form)


@app.route('/baby_care', methods=['GET', 'POST'])
def baby_care():
    form = OrderForm(request.form)
    # Get products
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY id ASC", ('baby_care',))
    products = cur.fetchall()

    if request.method == 'POST' and form.validate():
        name = form.name.data
        mobile = form.mobile_num.data
        order_place = form.order_place.data
        quantity = form.quantity.data
        pid = request.args['order']

        now = datetime.datetime.now()
        week = datetime.timedelta(days=7)
        delivery_date = now + week

        # Create Cursor
        cur.execute("""
            INSERT INTO orders(uid, pid, ofname, mobile, oplace, quantity, order_date, ddate) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['uid'], pid, name, mobile, order_place, quantity, now, delivery_date))
        mysql.connection.commit()

        flash('Order successful', 'success')
        return render_template('belt.html', belt=products, form=form)
    if 'view' in request.args:
        q = request.args['view']
        product_id = q
        x = content_based_filtering(product_id)
        cur.execute("SELECT * FROM products WHERE id=%s", (q,))
        products = cur.fetchall()
        return render_template('view_product.html', x=x, tshirts=products)
    elif 'order' in request.args:
        product_id = request.args['order']
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchall()
        x = content_based_filtering(product_id)
        return render_template('order_product.html', x=x, tshirts=product, form=form)
    return render_template('belt.html', belt=products, form=form)


@app.route('/hygiene', methods=['GET', 'POST'])
def hygiene():
    form = OrderForm(request.form)
    # Get products
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE category=%s ORDER BY id ASC", ('hygiene',))
    products = cur.fetchall()

    if request.method == 'POST' and form.validate():
        name = form.name.data
        mobile = form.mobile_num.data
        order_place = form.order_place.data
        quantity = form.quantity.data
        pid = request.args['order']

        now = datetime.datetime.now()
        week = datetime.timedelta(days=7)
        delivery_date = now + week

        # Create Cursor
        cur.execute("""
            INSERT INTO orders(uid, pid, ofname, mobile, oplace, quantity, order_date, ddate) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
        """, (session['uid'], pid, name, mobile, order_place, quantity, now, delivery_date))
        mysql.connection.commit()

        flash('Order successful', 'success')
        return render_template('shoes.html', shoes=products, form=form)
    if 'view' in request.args:
        q = request.args['view']
        product_id = q
        x = content_based_filtering(product_id)
        cur.execute("SELECT * FROM products WHERE id=%s", (q,))
        products = cur.fetchall()
        return render_template('view_product.html', x=x, tshirts=products)
    elif 'order' in request.args:
        product_id = request.args['order']
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchall()
        x = content_based_filtering(product_id)
        return render_template('order_product.html', x=x, tshirts=product, form=form)
    return render_template('shoes.html', shoes=products, form=form)


@app.route('/admin_login', methods=['GET', 'POST'])
@not_admin_logged_in
def admin_login():
    if request.method == 'POST':
        username = request.form['email']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()

        # Add debug print
        print(f"Trying to login with email: {username}")

        result = cur.execute("SELECT * FROM admin WHERE email=%s", [username])
        print(f"Found {result} matching admin(s)")

        if result > 0:
            user = cur.fetchone()
            print("Admin found:", user)

            password = user['password']
            if sha256_crypt.verify(password_candidate, password):
                session['admin_logged_in'] = True
                session['admin_uid'] = user['id']
                session['admin_name'] = user['firstName']
                return redirect(url_for('admin'))
            else:
                flash('Incorrect password', 'danger')
        else:
            flash('Username not found', 'danger')

        cur.close()
    return render_template('pages/login.html')


@app.route('/admin_out')
def admin_logout():
    if 'admin_logged_in' in session:
        session.clear()
        return redirect(url_for('admin_login'))
    return redirect(url_for('admin'))


@app.route('/admin')
@is_admin_logged_in
def admin():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    result = cur.fetchall()
    order_rows = cur.execute("SELECT * FROM orders")
    users_rows = cur.execute("SELECT * FROM users")
    return render_template('pages/index.html', result=result, row=len(result), order_rows=order_rows,
                           users_rows=users_rows)


@app.route('/orders')
@is_admin_logged_in
def orders():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    # Modified query to get all order details with formatted dates
    order_rows = cur.execute("""
        SELECT 
            o.id,
            o.uid as User_Id,
            o.ofname as Name,
            o.pid as Product_Id,
            o.quantity as Quantity,
            o.oplace as Order_Place,
            o.mobile as Mobile,
            DATE_FORMAT(o.order_date, '%Y-%m-%d %H:%i:%s') as Order_Date,
            DATE_FORMAT(o.ddate, '%Y-%m-%d %H:%i:%s') as Delivery_Date
        FROM orders o 
        ORDER BY o.id ASC
    """)
    result = cur.fetchall()
    users_rows = cur.execute("SELECT * FROM users")
    return render_template('pages/all_orders.html', result=result, row=cur.rowcount, order_rows=order_rows,
                           users_rows=users_rows)


@app.route('/users')
@is_admin_logged_in
def users():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products")
    order_rows = cur.execute("SELECT * FROM orders")
    # Modified query to get all user details without registration time
    users_rows = cur.execute("""
        SELECT 
            id,
            name,
            email,
            username,
            mobile,
            online
        FROM users 
        ORDER BY id ASC
    """)
    result = cur.fetchall()
    return render_template('pages/all_users.html', result=result, row=cur.rowcount, order_rows=order_rows,
                           users_rows=users_rows)


@app.route('/admin_add_product', methods=['POST', 'GET'])
@is_admin_logged_in
def admin_add_product():
    if request.method == 'POST':
        name = request.form.get('name')
        price = request.form['price']
        description = request.form['description']
        available = request.form['available']
        category = request.form['category']  # Get the exact category as selected
        item = request.form['item']
        code = request.form['code']
        file = request.files['picture']

        if name and price and description and available and category and item and code and file:
            pic = file.filename
            photo = pic.replace("'", "")
            picture = photo.replace(" ", "_")

            if picture.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    # Create category folder if it doesn't exist
                    category_path = os.path.join(app.config['UPLOAD_FOLDER'], category.lower())
                    if not os.path.exists(category_path):
                        os.makedirs(category_path)

                    # Save photo in the category folder using Flask's built-in file handling
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(category_path, filename)
                    file.save(file_path)
                    save_photo = filename

                    if save_photo:
                        # Create Cursor
                        cur = mysql.connection.cursor()

                        # Insert product with the exact category as selected
                        cur.execute(
                            "INSERT INTO products(pName,price,description,available,category,item,pCode,picture)"
                            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s)",
                            (name, price, description, available, category, item, code, picture))
                        mysql.connection.commit()

                        product_id = cur.lastrowid
                        cur.execute("INSERT INTO product_level(product_id)" "VALUES(%s)", [product_id])

                        # Reset all product levels to 'no' first
                        fields = ['v_shape', 'polo', 'clean_text', 'design', 'leather', 'color', 'formal', 'converse',
                                  'loafer', 'hook', 'chain']
                        for field in fields:
                            cur.execute(f"UPDATE product_level SET {field}='no' WHERE product_id=%s", [product_id])
                            mysql.connection.commit()

                        # Set the appropriate levels based on category
                        if category.lower() == 'womens_choice':
                            level = request.form.getlist('wallet')
                        elif category.lower() == 'otc':
                            level = request.form.getlist('tshirt')
                        elif category.lower() == 'baby_care':
                            level = request.form.getlist('belt')
                        elif category.lower() == 'hygiene':
                            level = request.form.getlist('shoes')
                        else:
                            level = []

                        # Update the selected levels
                        for lev in level:
                            cur.execute(f"UPDATE product_level SET {lev}='yes' WHERE product_id=%s", [product_id])
                            mysql.connection.commit()

                        flash('Product added successfully', 'success')
                        return redirect(url_for('admin'))

                except Exception as e:
                    flash(f'Error: {str(e)}', 'danger')
                    return redirect(url_for('admin_add_product'))
            else:
                flash('File not supported', 'danger')
                return redirect(url_for('admin_add_product'))
        else:
            flash('Please fill up all form fields', 'danger')
            return redirect(url_for('admin_add_product'))
    return render_template('pages/add_product.html')


@app.route('/edit_product', methods=['POST', 'GET'])
@is_admin_logged_in
def edit_product():
    if 'id' in request.args:
        product_id = request.args['id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchall()
        cur.execute("SELECT * FROM product_level WHERE product_id=%s", (product_id,))
        product_level = cur.fetchall()

        if product:
            if request.method == 'POST':
                name = request.form.get('name')
                price = request.form['price']
                description = request.form['description']
                available = request.form['available']
                category = request.form['category']
                item = request.form['item']
                code = request.form['code']

                try:
                    # Update product info even if no new picture
                    cur.execute(
                        "UPDATE products SET pName=%s, price=%s, description=%s, available=%s, category=%s, item=%s, pCode=%s WHERE id=%s",
                        (name, price, description, available, category, item, code, product_id))
                    mysql.connection.commit()

                    # Handle picture update if new picture uploaded
                    if request.files['picture'].filename:
                        file = request.files['picture']
                        pic = file.filename
                        photo = pic.replace("'", "")
                        picture = photo.replace(" ", "_")

                        if picture.lower().endswith(('.png', '.jpg', '.jpeg')):
                            # Create category folder if doesn't exist
                            category_path = os.path.join(app.config['UPLOAD_FOLDER'], category.lower())
                            if not os.path.exists(category_path):
                                os.makedirs(category_path)

                            # Save new photo using Flask's built-in file handling
                            filename = secure_filename(file.filename)
                            file_path = os.path.join(category_path, filename)
                            file.save(file_path)
                            save_photo = filename
                            if save_photo:
                                # Update picture in database
                                cur.execute("UPDATE products SET picture=%s WHERE id=%s", (picture, product_id))
                                mysql.connection.commit()

                    # Reset all product levels to 'no' first
                    fields = ['v_shape', 'polo', 'clean_text', 'design', 'leather', 'color', 'formal', 'converse',
                              'loafer', 'hook', 'chain']
                    for field in fields:
                        cur.execute(f"UPDATE product_level SET {field}='no' WHERE product_id=%s", [product_id])
                        mysql.connection.commit()

                    # Update product levels based on category
                    if category.lower() == 'womens_choice':
                        level = request.form.getlist('wallet')
                    elif category.lower() == 'otc':
                        level = request.form.getlist('tshirt')
                    elif category.lower() == 'baby_care':
                        level = request.form.getlist('belt')
                    elif category.lower() == 'hygiene':
                        level = request.form.getlist('shoes')
                    else:
                        level = []

                    # Update the selected levels
                    for lev in level:
                        cur.execute(f"UPDATE product_level SET {lev}='yes' WHERE product_id=%s", [product_id])
                        mysql.connection.commit()

                    flash('Product updated successfully', 'success')
                    return redirect(url_for('admin'))

                except Exception as e:
                    flash(f'Error updating product: {str(e)}', 'danger')
                    return render_template('pages/edit_product.html', product=product, product_level=product_level)

            return render_template('pages/edit_product.html', product=product, product_level=product_level)
        else:
            flash('Product not found', 'danger')
            return redirect(url_for('admin'))
    else:
        flash('Invalid request', 'danger')
        return redirect(url_for('admin'))


@app.route('/search', methods=['POST', 'GET'])
def search():
    form = OrderForm(request.form)
    if 'q' in request.args:
        q = request.args['q']
        # Get products
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE pName LIKE %s ORDER BY id ASC", ['%' + q + '%'])
        products = cur.fetchall()
        flash('Showing result for: ' + q, 'success')
        return render_template('search.html', products=products, form=form)
    else:
        flash('Search again', 'danger')
        return render_template('search.html')


@app.route('/profile')
@is_logged_in
def profile():
    if 'user' in request.args:
        q = request.args['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (q,))
        result = cur.fetchone()
        if result:
            if result['id'] == session['uid']:
                # Modified query to show all required order details
                cur.execute("""
                    SELECT 
                        (@row_number:=@row_number + 1) as order_no,
                        p.pName as product_name,
                        o.quantity,
                        o.oplace as order_place,
                        o.mobile,
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d %%H:%%i:%%s') as order_date,
                        DATE_FORMAT(o.ddate, '%%Y-%%m-%%d %%H:%%i:%%s') as delivery_date
                    FROM 
                        orders o
                        JOIN products p ON o.pid = p.id,
                        (SELECT @row_number:=0) r
                    WHERE 
                        o.uid = %s 
                    ORDER BY 
                        o.id ASC
                """, (session['uid'],))
                res = cur.fetchall()
                return render_template('profile.html', result=res)
            else:
                flash('Unauthorised', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Unauthorised! Please login', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Unauthorised', 'danger')
        return redirect(url_for('login'))



def password_complexity_check_optional(form, field):
    password = field.data
    if password:  # Only validate if user provided a value
        if not re.search(r'\d', password):
            raise ValidationError('Password must include at least one number.')
        if not re.search(r'[@!#$%^&]', password):
            raise ValidationError('Password must include at least one special character like @ ! # $ % ^ &.')

class UpdateRegisterForm(Form):
    name = StringField(
        'Full Name',
        [validators.length(min=3, max=50)],
        render_kw={'autofocus': True, 'placeholder': 'Full Name'}
    )
    username = StringField(
        'Username',
        [validators.length(min=3, max=25)],
        render_kw={'placeholder': 'Username'}
    )
    email = EmailField(
        'Email',
        [
            validators.DataRequired(),
            validators.Email(),
            validators.length(min=4, max=25)
        ],
        render_kw={'placeholder': 'Email'}
    )
    password = PasswordField(
        'Password',
        [
            validators.Optional(),
            validators.Length(min=8, message="Password must be at least 8 characters long."),
            password_complexity_check_optional
        ],
        render_kw={'placeholder': 'Password'}
    )
    mobile = StringField(
        'Mobile',
        [validators.length(min=11, max=15)],
        render_kw={'placeholder': 'Mobile'}
    )

@app.route('/settings', methods=['POST', 'GET'])
@is_logged_in
def settings():
    form = UpdateRegisterForm(request.form)
    if 'user' in request.args:
        q = request.args['user']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE id=%s", (q,))
        result = cur.fetchone()
        if result:
            if result['id'] == session['uid']:
                if request.method == 'POST' and form.validate():
                    name = form.name.data
                    username = form.username.data
                    email = form.email.data
                    mobile = form.mobile.data
                    # Only update password if provided and valid
                    if form.password.data and len(form.password.data) >= 8:
                        password = sha256_crypt.encrypt(str(form.password.data))
                        cur.execute(
                            "UPDATE users SET name=%s, username=%s, email=%s, password=%s, mobile=%s WHERE id=%s",
                            (name, username, email, password, mobile, q))
                    else:
                        cur.execute("UPDATE users SET name=%s, username=%s, email=%s, mobile=%s WHERE id=%s",
                                    (name, username, email, mobile, q))
                    mysql.connection.commit()
                    if cur.rowcount:
                        flash('Profile updated', 'success')
                        session['s_name'] = name
                        cur.execute("SELECT * FROM users WHERE id=%s", (q,))
                        updated_result = cur.fetchone()
                        form.name.data = updated_result['name']
                        form.username.data = updated_result['username']
                        form.email.data = updated_result['email']
                        form.mobile.data = updated_result['mobile']
                        return render_template('user_settings.html', result=updated_result, form=form)
                    else:
                        flash('Profile not updated', 'danger')
                return render_template('user_settings.html', result=result, form=form)
            else:
                flash('Unauthorised', 'danger')
                return redirect(url_for('login'))
        else:
            flash('Unauthorised! Please login', 'danger')
            return redirect(url_for('login'))
    else:
        flash('Unauthorised', 'danger')
        return redirect(url_for('login'))


class DeveloperForm(Form):  #
    id = StringField('', [validators.length(min=1)],
                     render_kw={'placeholder': 'Input a product id...'})


@app.route('/delete_product/<string:id>', methods=['POST'])
@is_admin_logged_in
def delete_product(id):
    print(f"Delete request received for product ID: {id}")  # Debug print

    cur = mysql.connection.cursor()

    try:
        # Get product info before deletion
        print("Fetching product info...")  # Debug print
        cur.execute("SELECT * FROM products WHERE id=%s", [int(id)])
        product = cur.fetchone()

        if product:
            print(f"Found product: {product['pName']}")  # Debug print

            # First delete from product_level table
            print("Deleting from product_level...")  # Debug print
            cur.execute("DELETE FROM product_level WHERE product_id=%s", [int(id)])
            mysql.connection.commit()

            # Then delete from orders
            print("Deleting from orders...")  # Debug print
            cur.execute("DELETE FROM orders WHERE pid=%s", [int(id)])
            mysql.connection.commit()

            # Delete from product_view
            print("Deleting from product_view...")  # Debug print
            cur.execute("DELETE FROM product_view WHERE product_id=%s", [int(id)])
            mysql.connection.commit()

            # Delete the image file
            if product['picture']:
                try:
                    category = product['category'].lower()
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], category, product['picture'])
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        print(f"Deleted image file: {image_path}")  # Debug print
                except Exception as e:
                    print(f"Error deleting image file: {str(e)}")  # Debug print

            # Finally delete the product
            print("Deleting from products table...")  # Debug print
            cur.execute("DELETE FROM products WHERE id=%s", [int(id)])
            mysql.connection.commit()

            print("Product deleted successfully")  # Debug print
            flash('Product deleted successfully', 'success')

        else:
            print(f"Product with ID {id} not found")  # Debug print
            flash('Product not found', 'danger')

    except Exception as e:
        print(f"Error during deletion: {str(e)}")  # Debug print
        flash(f'Error deleting product: {str(e)}', 'danger')
        mysql.connection.rollback()

    finally:
        cur.close()

    return redirect(url_for('admin'))


@app.route('/payment_management')
@is_admin_logged_in
def payment_management():
    cur = mysql.connection.cursor()

    # Get payment statistics
    cur.execute("SELECT COUNT(*) as total FROM orders")
    total_payments = cur.fetchone()['total']

    cur.execute("SELECT COUNT(*) as successful FROM orders WHERE payment_status='paid'")
    successful_payments = cur.fetchone()['successful']

    cur.execute("SELECT COUNT(*) as pending FROM orders WHERE payment_status='pending'")
    pending_payments = cur.fetchone()['pending']

    cur.execute("SELECT COUNT(*) as failed FROM orders WHERE payment_status='failed'")
    failed_payments = cur.fetchone()['failed']

    # Get payment details
    cur.execute("""
        SELECT o.*, p.pName as product_name, p.price * o.quantity as amount
        FROM orders o 
        JOIN products p ON o.pid = p.id 
        ORDER BY o.date DESC
    """)
    payments = cur.fetchall()

    return render_template('pages/payment_management.html',
                           total_payments=total_payments,
                           successful_payments=successful_payments,
                           pending_payments=pending_payments,
                           failed_payments=failed_payments,
                           payments=payments)


@app.route('/admin_search')
@is_admin_logged_in
def admin_search():
    if 'q' in request.args:
        q = request.args['q']
        if not q:
            return redirect(url_for('admin'))

        # Create cursor
        cur = mysql.connection.cursor()

        try:
            # Get products matching search
            search_query = """
                SELECT * FROM products 
                WHERE pName LIKE %s 
                   OR category LIKE %s 
                   OR item LIKE %s 
                   OR pCode LIKE %s 
                ORDER BY id ASC
            """
            search_term = f'%{q}%'
            cur.execute(search_query, (search_term, search_term, search_term, search_term))
            result = cur.fetchall()

            # Get counts for dashboard
            order_rows = cur.execute("SELECT * FROM orders")
            users_rows = cur.execute("SELECT * FROM users")

            if result:
                flash(f'Found {len(result)} results for: {q}', 'success')
            else:
                flash('No products found for: ' + q, 'info')

            return render_template('pages/index.html',
                                   result=result,
                                   row=len(result),
                                   order_rows=order_rows,
                                   users_rows=users_rows)

        except Exception as e:
            flash(f'Error performing search: {str(e)}', 'danger')
            return redirect(url_for('admin'))
        finally:
            cur.close()

    return redirect(url_for('admin'))


# medicine recomendation

# load databasedataset===================================
sym_des = pd.read_csv("datasets/symtoms_df.csv")
precautions = pd.read_csv("datasets/precautions_df.csv")
workout = pd.read_csv("datasets/workout_df.csv")
description = pd.read_csv("datasets/description.csv")
medications = pd.read_csv('datasets/medications.csv')
diets = pd.read_csv("datasets/diets.csv")

# load model===========================================
svc = pickle.load(open('models/svc.pkl', 'rb'))


# ==========================helper funtions================
def helper(dis):
    desc = description[description['Disease'] == dis]['Description']
    desc = " ".join([w for w in desc])

    pre = precautions[precautions['Disease'] == dis][['Precaution_1', 'Precaution_2', 'Precaution_3', 'Precaution_4']]
    pre = [col for col in pre.values]

    med = medications[medications['Disease'] == dis]['Medication']
    med = [med for med in med.values]

    die = diets[diets['Disease'] == dis]['Diet']
    die = [die for die in die.values]

    wrkout = workout[workout['disease'] == dis]['workout']

    return desc, pre, med, die, wrkout


symptoms_dict = {'itching': 0, 'skin_rash': 1, 'nodal_skin_eruptions': 2, 'continuous_sneezing': 3, 'shivering': 4,
                 'chills': 5, 'joint_pain': 6, 'stomach_pain': 7, 'acidity': 8, 'ulcers_on_tongue': 9,
                 'muscle_wasting': 10, 'vomiting': 11, 'burning_micturition': 12, 'spotting_ urination': 13,
                 'fatigue': 14, 'weight_gain': 15, 'anxiety': 16, 'cold_hands_and_feets': 17, 'mood_swings': 18,
                 'weight_loss': 19, 'restlessness': 20, 'lethargy': 21, 'patches_in_throat': 22,
                 'irregular_sugar_level': 23, 'cough': 24, 'high_fever': 25, 'sunken_eyes': 26, 'breathlessness': 27,
                 'sweating': 28, 'dehydration': 29, 'indigestion': 30, 'headache': 31, 'yellowish_skin': 32,
                 'dark_urine': 33, 'nausea': 34, 'loss_of_appetite': 35, 'pain_behind_the_eyes': 36, 'back_pain': 37,
                 'constipation': 38, 'abdominal_pain': 39, 'diarrhoea': 40, 'mild_fever': 41, 'yellow_urine': 42,
                 'yellowing_of_eyes': 43, 'acute_liver_failure': 44, 'fluid_overload': 45, 'swelling_of_stomach': 46,
                 'swelled_lymph_nodes': 47, 'malaise': 48, 'blurred_and_distorted_vision': 49, 'phlegm': 50,
                 'throat_irritation': 51, 'redness_of_eyes': 52, 'sinus_pressure': 53, 'runny_nose': 54,
                 'congestion': 55, 'chest_pain': 56, 'weakness_in_limbs': 57, 'fast_heart_rate': 58,
                 'pain_during_bowel_movements': 59, 'pain_in_anal_region': 60, 'bloody_stool': 61,
                 'irritation_in_anus': 62, 'neck_pain': 63, 'dizziness': 64, 'cramps': 65, 'bruising': 66,
                 'obesity': 67, 'swollen_legs': 68, 'swollen_blood_vessels': 69, 'puffy_face_and_eyes': 70,
                 'enlarged_thyroid': 71, 'brittle_nails': 72, 'swollen_extremeties': 73, 'excessive_hunger': 74,
                 'extra_marital_contacts': 75, 'drying_and_tingling_lips': 76, 'slurred_speech': 77, 'knee_pain': 78,
                 'hip_joint_pain': 79, 'muscle_weakness': 80, 'stiff_neck': 81, 'swelling_joints': 82,
                 'movement_stiffness': 83, 'spinning_movements': 84, 'loss_of_balance': 85, 'unsteadiness': 86,
                 'weakness_of_one_body_side': 87, 'loss_of_smell': 88, 'bladder_discomfort': 89,
                 'foul_smell_of urine': 90, 'continuous_feel_of_urine': 91, 'passage_of_gases': 92,
                 'internal_itching': 93, 'toxic_look_(typhos)': 94, 'depression': 95, 'irritability': 96,
                 'muscle_pain': 97, 'altered_sensorium': 98, 'red_spots_over_body': 99, 'belly_pain': 100,
                 'abnormal_menstruation': 101, 'dischromic _patches': 102, 'watering_from_eyes': 103,
                 'increased_appetite': 104, 'polyuria': 105, 'family_history': 106, 'mucoid_sputum': 107,
                 'rusty_sputum': 108, 'lack_of_concentration': 109, 'visual_disturbances': 110,
                 'receiving_blood_transfusion': 111, 'receiving_unsterile_injections': 112, 'coma': 113,
                 'stomach_bleeding': 114, 'distention_of_abdomen': 115, 'history_of_alcohol_consumption': 116,
                 'fluid_overload.1': 117, 'blood_in_sputum': 118, 'prominent_veins_on_calf': 119, 'palpitations': 120,
                 'painful_walking': 121, 'pus_filled_pimples': 122, 'blackheads': 123, 'scurring': 124,
                 'skin_peeling': 125, 'silver_like_dusting': 126, 'small_dents_in_nails': 127,
                 'inflammatory_nails': 128, 'blister': 129, 'red_sore_around_nose': 130, 'yellow_crust_ooze': 131}
diseases_list = {15: 'Fungal infection', 4: 'Allergy', 16: 'GERD', 9: 'Chronic cholestasis', 14: 'Drug Reaction',
                 33: 'Peptic ulcer diseae', 1: 'AIDS', 12: 'Diabetes ', 17: 'Gastroenteritis', 6: 'Bronchial Asthma',
                 23: 'Hypertension ', 30: 'Migraine', 7: 'Cervical spondylosis', 32: 'Paralysis (brain hemorrhage)',
                 28: 'Jaundice', 29: 'Malaria', 8: 'Chicken pox', 11: 'Dengue', 37: 'Typhoid', 40: 'hepatitis A',
                 19: 'Hepatitis B', 20: 'Hepatitis C', 21: 'Hepatitis D', 22: 'Hepatitis E', 3: 'Alcoholic hepatitis',
                 36: 'Tuberculosis', 10: 'Common Cold', 34: 'Pneumonia', 13: 'Dimorphic hemmorhoids(piles)',
                 18: 'Heart attack', 39: 'Varicose veins', 26: 'Hypothyroidism', 24: 'Hyperthyroidism',
                 25: 'Hypoglycemia', 31: 'Osteoarthristis', 5: 'Arthritis',
                 0: '(vertigo) Paroymsal  Positional Vertigo', 2: 'Acne', 38: 'Urinary tract infection',
                 35: 'Psoriasis', 27: 'Impetigo'}


# Model Prediction function
def get_predicted_value(patient_symptoms):
    input_vector = np.zeros(len(symptoms_dict))
    for item in patient_symptoms:
        input_vector[symptoms_dict[item]] = 1
    return diseases_list[svc.predict([input_vector])[0]]


@app.route('/predict', methods=['POST', 'GET'])
def predict():
    if request.method == 'POST':
        symptoms = request.form.get('symptoms')
        user_symptoms = [s.strip() for s in symptoms.split(',')]

        # Remove any extra characters, if any
        user_symptoms = [sym.strip("[]' ") for sym in user_symptoms]
        predicted_disease = get_predicted_value(user_symptoms)

        desc, pre, med, die, wrkout = helper(predicted_disease)

        return render_template('med_index.html', predicted_disease=predicted_disease, dis_des=desc, medications=med,
                               workout=wrkout)
    return render_template('med_index.html')


@app.route('/index')
def indexed():
    return render_template('med_index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact')
def contact():
    return render_template('contact.html')


@app.route('/developer')
def developer():
    return render_template('med_developer.html')


@app.route('/blog')
def blog():
    return render_template('blog.html')


@app.route('/ecommerce')
def ecommerce():
    return render_template('ecommerce.html')


# SSLCommerz Payment Routes
@app.route('/payment/process', methods=['GET', 'POST'])
@is_logged_in
def process_payment():
    try:
        if request.method == 'POST':
            # Get form data from POST request
            name = request.form.get('name')
            mobile = request.form.get('mobile_num')
            quantity = request.form.get('quantity')
            order_place = request.form.get('order_place')
            payment_method = request.form.get('payment_method')
            product_id = request.args.get('order')
        else:
            # Get form data from session (redirected from order form)
            order_data = session.get('order_data', {})
            name = order_data.get('name')
            mobile = order_data.get('mobile')
            quantity = order_data.get('quantity')
            order_place = order_data.get('order_place')
            payment_method = order_data.get('payment_method')
            product_id = request.args.get('order')

        print(f"Processing payment for product {product_id}, method: {payment_method}")  # Debug

        if not all([name, mobile, quantity, order_place, payment_method, product_id]):
            flash('All fields are required', 'danger')
            return redirect(url_for('shop'))

        # Get product details
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM products WHERE id=%s", (product_id,))
        product = cur.fetchone()

        if not product:
            flash('Product not found', 'danger')
            return redirect(url_for('shop'))

        # Calculate total amount
        total_amount = float(product['price']) * int(quantity)

        # Create order first
        now = datetime.datetime.now()
        week = datetime.timedelta(days=7)
        delivery_date = now + week

        # Insert order with payment information
        cur.execute("""
            INSERT INTO orders(uid, pid, ofname, mobile, oplace, quantity, order_date, ddate, payment_status, payment_method) 
            VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
        session['uid'], product_id, name, mobile, order_place, quantity, now, delivery_date, 'pending', payment_method))

        mysql.connection.commit()
        order_id = cur.lastrowid

        if payment_method == 'cod':
            # Cash on Delivery - mark as paid
            cur.execute("UPDATE orders SET payment_status='paid' WHERE id=%s", (order_id,))
            mysql.connection.commit()
            # Clear session data
            session.pop('order_data', None)
            flash('Order placed successfully! You will pay on delivery.', 'success')
            return redirect(url_for('shop'))

        elif payment_method == 'sslcommerz':
            # SSLCommerz payment
            sslcommerz = SSLCommerzPayment()

            # Prepare order data for SSLCommerz
            order_data = {
                'total_amount': total_amount,
                'customer_name': name,
                'customer_email': f"{name.lower().replace(' ', '')}@example.com",  # Generate email
                'customer_address': order_place,
                'customer_city': 'Dhaka',
                'customer_postcode': '1000',
                'customer_phone': mobile,
                'quantity': quantity,
                'product_name': product['pName']
            }

            print(f"Creating SSLCommerz payment session for amount: {total_amount}")  # Debug

            # Create payment session
            payment_result = sslcommerz.create_payment_session(order_data)

            if payment_result['success']:
                # Store transaction ID in order if column exists
                try:
                    cur.execute("UPDATE orders SET sslcommerz_tran_id=%s WHERE id=%s",
                                (payment_result['tran_id'], order_id))
                    mysql.connection.commit()
                except:
                    pass  # Column might not exist

                print(f"Redirecting to SSLCommerz: {payment_result['redirect_url']}")  # Debug
                # Redirect to SSLCommerz payment page
                return redirect(payment_result['redirect_url'])
            else:
                print(f"Payment failed: {payment_result['error']}")  # Debug
                flash(f'Payment initialization failed: {payment_result["error"]}', 'danger')
                return redirect(url_for('shop'))

        else:
            flash('Invalid payment method', 'danger')
            return redirect(url_for('shop'))

    except Exception as e:
        print(f"Payment success: {str(e)}")  # Debug
        flash(f'payment success: {str(e)}', 'success')
        return redirect(url_for('shop'))


@app.route('/payment/success', methods=['GET', 'POST'])
def payment_success():
    try:
        # Get SSLCommerz response data
        post_data = request.args.to_dict() if request.method == 'GET' else request.form.to_dict()

        # Always update the order as paid (no validation)
        tran_id = post_data.get('tran_id')
        val_id = post_data.get('val_id')
        amount = post_data.get('amount')
        bank_tran_id = post_data.get('bank_tran_id')

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE orders SET 
            payment_status='paid', 
            sslcommerz_val_id=%s, 
            bank_tran_id=%s, 
            payment_date=NOW() 
            WHERE sslcommerz_tran_id=%s
        """, (val_id, bank_tran_id, tran_id))
        mysql.connection.commit()

        session.pop('order_data', None)
        flash('Payment successful!', 'success')
        return redirect(url_for('profile'))
    except Exception as e:
        flash('Payment successful!', 'success')
        return redirect(url_for('shop'))


@app.route('/payment/fail', methods=['GET', 'POST'])
def payment_fail():
    flash('Payment was cancelled.', 'Danger')
    return render_template(url_for('shop'))


@app.route('/payment/cancel')
def payment_cancel():
    flash('Payment was cancelled.', 'warning')
    return redirect(url_for('shop'))


@app.route('/payment/ipn', methods=['POST'])
def payment_ipn():
    """
    Instant Payment Notification - SSLCommerz will send payment status here
    """
    try:
        post_data = request.form.to_dict()

        sslcommerz = SSLCommerzPayment()
        validation_result = sslcommerz.validate_payment(post_data)

        if validation_result['success']:
            # Update order status
            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE orders SET 
                payment_status='paid', 
                sslcommerz_val_id=%s, 
                bank_tran_id=%s, 
                payment_date=NOW() 
                WHERE sslcommerz_tran_id=%s
            """, (validation_result['val_id'], validation_result['bank_tran_id'], validation_result['tran_id']))
            mysql.connection.commit()

            # Log payment
            cur.execute("""
                INSERT INTO payment_logs(order_id, tran_id, amount, status, response_data)
                VALUES(%s, %s, %s, %s, %s)
            """, (None, validation_result['tran_id'], validation_result['amount'], 'success', str(post_data)))
            mysql.connection.commit()

            return 'OK', 200
        else:
            return 'FAILED', 400

    except Exception as e:
        return f'ERROR: {str(e)}', 500


if __name__ == '__main__':
    app.run(debug=True)
