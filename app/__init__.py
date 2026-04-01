from flask import Flask
from flask_socketio import SocketIO
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.static_folder = os.path.join(base_dir, 'static')
app.template_folder = os.path.join(base_dir, 'templates')

socketio = SocketIO(app)

from app.routes.main import *