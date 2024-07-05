from flask import Flask, render_template, redirect, url_for, request, flash
import mysql.connector
import os
import requests
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SESSION_SECRET_KEY")

key = os.environ.get('LANGUAGE_KEY')
endpoint = os.environ.get('LANGUAGE_ENDPOINT')
print(key, endpoint, end="/n")

from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

# Authenticate the client using your key and endpoint 
def authenticate_client():
    ta_credential = AzureKeyCredential(str(key))
    text_analytics_client = TextAnalyticsClient(
            endpoint=str(endpoint), 
            credential=ta_credential)
    return text_analytics_client

client = authenticate_client()

def create_database_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("SESSION_DB_HOST"),
            database=os.getenv("SESSION_DB"),
            user=os.getenv("SESSION_DB_USER"),
            password=os.getenv("SESSION_DB_PWD")
        )
        print("MySQL Database connection successful")
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

def create_database(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("Database created successfully")
    except Error as e:
        print(f"The error '{e}' occurred")

def create_table(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        print("Table created successfully")
    except Error as e:
        print(f"The error '{e}' occurred")

@app.route('/')
def home():
    return render_template('main.html')

@app.route('/login', methods=['POST'])
def login():
    # Here you would add logic to validate login credentials
    # For now, we'll just redirect to the main page
    email = request.form['email']
    password = request.form['password']  # In a real app, use hashed passwords
    if email=="admin@gmail.com":
        return render_template('index.html')
    conn = create_database_connection()
    create_users_table = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
"""

    create_table(conn, create_users_table)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM users WHERE email = %s", (email,))
        record = cursor.fetchone()
        if record:
            stored_password = record[0]
            if password == stored_password:  # Replace this line with hashed password check in production
                # User is authenticated
                return render_template('index.html')  # Redirect to a home or dashboard page
            else:
                # Wrong password
                flash('Wrong password. Please try again!')
                return redirect(url_for('main'))
        else:
            # Email does not exist
            flash('User not found')
            return redirect(url_for('main'))
    except Error as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('main'))
    finally:
        cursor.close()
        conn.close()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']  # Consider hashing the password for security
        conn = create_database_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (email, password) VALUES (%s, %s)", (email, password))
            conn.commit()
            flash('User registered successfully!')
            return redirect(url_for('main'))  # Redirect to clear form
        except Error as e:
            flash('Error: ' + str(e), 'error')
        finally:
            cursor.close()
            conn.close()
    return render_template('main.html')

def sample_extractive_summarization(client, text):
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.textanalytics import (
        TextAnalyticsClient,
        ExtractiveSummaryAction
    ) 

    text+=" "
    document = [text]
    poller = client.begin_analyze_actions(
        document,
        actions=[
            ExtractiveSummaryAction(max_sentence_count=4)
        ],
    )

    document_results = poller.result()
    for result in document_results:
        extract_summary_result = result[0]  # first document, first result
        res = " ".join([sentence.text for sentence in extract_summary_result.sentences])
    return res

@app.route('/content', methods=['POST'])
def handle_content():
    text = request.form['text']  # Match the name attribute of your textarea
    model = request.form['model']
    if model=="azure":
        #res = sample_extractive_summarization(client, text)
        a = 1
    
    elif model=="mb":
        API_URL = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
        headers = {"Authorization": os.getenv("SESSION_API_AUTH")}
        payload = {
	                "inputs": text,
                    "options":{
                        "wait_for_model": "true" 
                    }
                    }
        response = requests.post(API_URL, headers=headers, json=payload)
        res = response.json()

    elif model=="fa":
        API_URL = "https://api-inference.huggingface.co/models/Falconsai/text_summarization"
        headers = {"Authorization": os.getenv("SESSION_API_AUTH")}
        payload = {
	                "inputs": text,
                    "options":{
                        "wait_for_model": "true" 
                    }
                    }
        response = requests.post(API_URL, headers=headers, json=payload)
        res = response.json()
        
    return render_template('index.html', summary_text = res[0].get('summary_text'))

@app.route('/main')
def main():
    # Render the main page
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)

    