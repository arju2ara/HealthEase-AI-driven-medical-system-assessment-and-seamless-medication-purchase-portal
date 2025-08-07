from passlib.hash import sha256_crypt
from flask_mysqldb import MySQL
from flask import Flask

app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'medicine'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

# Initialize MySQL
mysql = MySQL(app)

with app.app_context():
    try:
        # Create cursor
        cur = mysql.connection.cursor()
        
        # Admin details
        firstName = 'Admin'
        lastName = 'User'
        email = 'admin@gmail.com'
        password = sha256_crypt.encrypt('admin123')
        
        # Delete existing admin if any
        cur.execute("DELETE FROM admin WHERE email=%s", [email])
        
        # Insert admin with encrypted password
        cur.execute("INSERT INTO admin(firstName, lastName, email, password) VALUES(%s, %s, %s, %s)", 
                    (firstName, lastName, email, password))
        
        # Commit to DB
        mysql.connection.commit()
        
        # Verify insertion
        cur.execute("SELECT * FROM admin WHERE email=%s", [email])
        admin = cur.fetchone()
        if admin:
            print("Admin created successfully!")
            print(f"Email: {admin['email']}")
        else:
            print("Failed to create admin!")
            
        # Close connection
        cur.close()
        
    except Exception as e:
        print(f"Error: {str(e)}") 