from flask import Flask
from flask_socketio import SocketIO
import os
import secrets

app = Flask(__name__)

# 生产环境必须从环境变量读取 SECRET_KEY，避免硬编码泄露
_secret_key = os.environ.get('SECRET_KEY')
if not _secret_key:
    # 开发环境自动生成随机密钥（每次重启后 Session 会失效，仅用于本地开发）
    _secret_key = secrets.token_hex(32)
    print('[警告] SECRET_KEY 未设置，已自动生成临时密钥。生产环境请务必通过环境变量配置！')
app.config['SECRET_KEY'] = _secret_key

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app.static_folder = os.path.join(base_dir, 'static')
app.template_folder = os.path.join(base_dir, 'templates')

socketio = SocketIO(app)

from app.routes.main import *