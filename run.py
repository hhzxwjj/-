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
    
    # 读取环境变量配置
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))
    
    print(f'[*] 启动服务: http://{host}:{port}')
    print(f'[*] Debug模式: {debug_mode}')
    
    # 启动Flask-SocketIO应用
    # 注意：Windows环境下debug=True可能导致reloader与SocketIO冲突，建议生产环境使用debug=False
    socketio.run(app, debug=debug_mode, host=host, port=port, use_reloader=False)