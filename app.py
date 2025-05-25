from flask import Flask, render_template, request, redirect, session
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import mysql.connector
import numpy as np
import matplotlib.pyplot as plt
import os
import random

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

# Connect to MySQL database
def get_db_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',  # Change to your MySQL username
        password='',  # Change to your MySQL password
        database='agri_insights'
    )
    return conn

# Create tables if they don't exist
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            phone VARCHAR(15) NOT NULL,
            password VARCHAR(255) NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crop_predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            crop_type VARCHAR(255) NOT NULL,
            district VARCHAR(255) NOT NULL,
            year INT NOT NULL,
            predicted_price FLOAT NOT NULL,
            current_price FLOAT NOT NULL,
            prediction_date DATE NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Home route (renders index.html)
@app.route('/', methods=['GET', 'POST'])
def home():
    return render_template('index.html')

# Registration route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    name = request.form['name']
    email = request.form['email']
    phone = request.form['phone']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user already exists
    cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
    existing_user = cursor.fetchone()
    if existing_user:
        conn.close()
        return "User already registered. <a href='/'>Go back</a>"

    # Insert new user
    cursor.execute(
        'INSERT INTO users (username, name, email, phone, password) VALUES (%s, %s, %s, %s, %s)',
        (username, name, email, phone, password)
    )
    conn.commit()
    conn.close()
    session['user'] = username  # Set session

    return redirect('/registered')  # Go to registered page

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if user exists and password matches
    cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = username  # Set session
        return redirect('/input')  # Go to input page
    else:
        return "Invalid credentials. <a href='/'>Go back</a>"

# Registered page route
@app.route('/registered')
def registered():
    if 'user' not in session:  # Check if user is logged in
        return redirect('/')
    return render_template('index.html', registered=True)  # Show registered confirmation page

# Input page route
@app.route('/input', methods=['GET', 'POST'])
def input_page():
    if 'user' not in session:  # Check if user is logged in
        return redirect('/')
    return render_template('index.html', input=True)  # Show input form

# Prediction route
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:  # Ensure user is logged in
        return redirect('/')

    # Get crop details from form
    crop_type = request.form['crop_type']
    district = request.form['district']
    year = int(request.form['year'])

    # Load dataset from Excel
    data = pd.read_excel('D:/AgriData.xlsx')  # Ensure this file exists
    X = data[['Year']]
    y = data['Price (₹/ton)']

    # Train the Random Forest model
    model = RandomForestRegressor()
    model.fit(X, y)

    # Predict price for the given year
    predicted_price = float(model.predict([[year]])[0])  # Convert to native float

    # Generate a  current price (just for demonstration)
    current_price = predicted_price * (1 + np.random.uniform(-0.1, 0.1))  #  fluctuation

    # Get the current date
    prediction_date = pd.to_datetime('today').date()
    
    # Calculate prices for the next 5 years with  fluctuations
    future_years = np.array([year + i for i in range(1, 6)])
    future_prices = [predicted_price * (1 + random.uniform(-0.05, 0.05)) for _ in range(5)]

    # Save the plot of predicted future prices
    plt.figure(figsize=(10, 5))
    plt.plot(future_years, future_prices, marker='o', linestyle='-', color='green')
    plt.title(f'Predicted Prices for {crop_type} Over the Next 5 Years')
    plt.xlabel('Year')
    plt.ylabel('Price (₹/ton)')
    plt.grid()
    plot_path = 'D:static/prediction_plot.png'
    plt.savefig(plot_path)
    plt.close()


    # Save the prediction in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO crop_predictions (crop_type, district, year, predicted_price, current_price, prediction_date) VALUES (%s, %s, %s, %s, %s, %s)',
        (crop_type, district, year, predicted_price, current_price, prediction_date)
    )
    conn.commit()
    conn.close()

    return redirect('/prediction_result')  # Go to prediction result page

# Prediction result page route
@app.route('/prediction_result')
def prediction_result():
    if 'user' not in session:  # Ensure user is logged in
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT crop_type, district, year, predicted_price, current_price, prediction_date FROM crop_predictions ORDER BY id DESC LIMIT 1')
    latest_prediction = cursor.fetchone()
    conn.close()

    return render_template('index.html', prediction=latest_prediction)  # Show prediction result

# Logout route
@app.route('/logout')
def logout():
    session.pop('user', None)  # Clear session
    return redirect('/')

# Run the app
if __name__ == '__main__':
    create_tables()  # Ensure tables are created on startup
    app.run(debug=True)
