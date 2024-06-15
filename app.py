import os
import json
import time
import logging
from openai import OpenAI
from dotenv import load_dotenv
from flask import Flask, render_template, request, session
from mindsdb_sdk.utils.mind import create_mind as create_mindsdb_mind

from config import databases

# Configure logging to ignore Werkzeug's default logging messages
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# Load environment variables from a .env file
load_dotenv()

# Get the MindsDB API Key from the environment variables
mindsdb_api_key = os.getenv('MINDSDB_API_KEY')

#define base url
base_url = os.getenv('MINDSDB_API_URL', "https://llm.mdb.ai")
if base_url.endswith("/"):
    base_url = base_url[:-1]

# If the MindsDB API Key is not found, print an error message and exit
if not mindsdb_api_key:
    print("Please create a .env file and add your MindsDB API Key")
    exit()

# Create a Flask application instance
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))

# Create an instance of the OpenAI client with the MindsDB API Key and endpoint
client = OpenAI(
   api_key=mindsdb_api_key,
   base_url=base_url
)

# Mind arguments
model = 'gpt-4'  # This is the model used by MindsDB text to SQL, and is not limited by what our inference endpoints support.

# Define the route for the home page
@app.route('/')
def index():
    return render_template('index.html')  # Render the index.html template

# Define the route for the completions
@app.route('/llm')
def llm():
    return render_template('llm.html')  # Render the index.html template

@app.route('/database')
def get_databases():
    return render_template('databases.html')

@app.route('/database/<string:database_name>')
def get_database(database_name):
    form_elements = databases[database_name]
    return render_template('database.html', database_name=database_name, form_elements=form_elements)

@app.route('/mind', methods=['POST'])
def create_mind():
    # Get database name
    database_name = request.form['database_name']

    # Get expected database connection arguments
    database_args = databases[database_name]

    # Create connection arguments dictionary
    connection_args = {}
    for key, val in database_args.items():
        if val['type'] == 'number':
            connection_args[key] = int(request.form[key])
        else:
            connection_args[key] = request.form[key]

    # TODO: Add schema field to the form
    connection_args['schema'] = 'demo_data'

    # Get data description
    # TODO: Add a description field to the form
    # description = request.form['description']
    description = 'House Sales'

    # Generate a unique mind name
    ts = str(int(time.time()))
    mind_name = f"{database_name}_mind_{ts}"

    # Create a mind
    create_mindsdb_mind(
        name = mind_name,
        base_url=base_url,
        api_key=mindsdb_api_key,
        model=model,
        data_source_connection_args=connection_args,
        data_source_type='postgres',
        description=description
    )

    logging.info(f"Mind successfully created: {mind_name}")

    # Store the mind name in the session
    session['mind_name'] = mind_name

    return render_template('index.html')

# Define the route for sending a message
@app.route('/send', methods=['POST'])
def send():
    message = request.form['message']  # Get the message from the form
    res = [] 
    try:
        # Create the message object
        new_message = {"role": "user", "content": message}
        # Send the message to the API and get the response
        response = client.chat.completions.create(
            # The model provided must be the name of the mind.
            model=session['mind_name'],
            messages=[new_message],
            stream=False
        )

        print("Got response:")
        print(response)
        if not response.choices[0].message.content:
            res.append({
                "role": "error", 
                "content": "Something went wrong please try again later.", 
                "model": response.model,
                "usage": {
                    "completion_tokens": response.usage.completion_tokens, 
                    "prompt_tokens": response.usage.prompt_tokens, 
                    "total_tokens": response.usage.total_tokens
                }
            })
        else:
            # Append the assistant's response to the res list
            res.append({
                "role": "assistant", 
                "content": response.choices[0].message.content, 
                "model": response.model,
                "usage": {
                    "completion_tokens": response.usage.completion_tokens, 
                    "prompt_tokens": response.usage.prompt_tokens, 
                    "total_tokens": response.usage.total_tokens
                }
            })
    except Exception as e:
        # Handle different types of errors and append error messages to the res list
        print(e)
        if e.code == 400:
            res.append({"role": "error", "content": "Model not found. Please use one of our supported models https://docs.mdb.ai/docs/models"})
        if e.code == 401:
            res.append({"role": "error", "content": "Invalid MindsDB API Key, please verify your API key and update your .env file."})
        if e.code == 429:
            res.append({"role": "error", "content": "You have reached your message limit of 10 requests per minute per IP and, at most, 4 requests per IP in a 10-second period.  Please refer to the documentation for more details or contact us to raise your request limit."})
        elif e.code == 500:
            res.append({"role": "error", "content": "Internal system error. Please try again later."})

    # Return the updated res list
    return res  

@app.route('/send_llm', methods=['POST'])
def send_llm():
    message = request.form['message']  # Get the message from the form
    history = request.form.get('history') or False  # Get the history from the form
    model = request.form.get('model') or "gpt-3.5-turbo"  # Default to "gpt-3.5-turbo" if no model is provided
    print("Completing request using model: "+model)
    res = [] 
    try:
        # Create the message object
        new_message = [{"role": "user", "content": message}]
        if history and model != 'dbrx' and model != 'firefunction-v1' and model != 'firellava-13b' and model != 'hermes-2-pro':
            new_message = json.loads(history)
        print(new_message)
        # Send the message to the API and get the response
        response = client.chat.completions.create(
            model=model,   # This model is limited by what our inference endpoints support (only gpt-3.5-turbo for now).
            messages=new_message,
            stream=False
        )
        print("Got response:")
        print(response)
        
        # Append the assistant's response to the res list
        res.append({
            "role": "assistant", 
            "content": response.choices[0].message.content, 
            "model": response.model,
            "usage": {
                "completion_tokens": response.usage.completion_tokens, 
                "prompt_tokens": response.usage.prompt_tokens, 
                "total_tokens": response.usage.total_tokens
            }
        })
    except Exception as e:
        # Handle different types of errors and append error messages to the res list
        print(e)
        if e.code == 400:
            res.append({"role": "error", "content": "Model not found. Please use one of our supported models https://docs.mdb.ai/docs/models"})
        if e.code == 401:
            res.append({"role": "error", "content": "Invalid MindsDB API Key, please verify your API key and update your .env file."})
        if e.code == 429:
            res.append({"role": "error", "content": "You have reached your message limit of 10 requests per minute per IP and, at most, 4 requests per IP in a 10-second period.  Please refer to the documentation for more details or contact us to raise your request limit."})
        elif e.code == 500:
            res.append({"role": "error", "content": "Internal system error. Please try again later."})

    # Return the updated res list
    return res  

@app.route('/models', methods=['POST'])
def models():
    response = client.models.list()
    data = []
    for model in response:
        data.append(model.id)
    return data

# Run the Flask application
if __name__ == '__main__':
    print("App Running on 127.0.0.1:8000")
    app.run(port=8000, debug=True) 

