#!/usr/bin/env python3
"""
启动书法培训班管理系统
"""

import os
from app import app, socketio
from app.models.database import init_db
from app.routes.main import init_admin

if __name__ == '__main__':
    # 初始化数据库
    init_db()
    # 初始化管理员账户
    init_admin()
    # 创建templates目录
    if not os.path.exists('templates'):
        os.makedirs('templates')
    # 创建static目录
    if not os.path.exists('static'):
        os.makedirs('static')
    # 启动Flask-SocketIO应用
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)