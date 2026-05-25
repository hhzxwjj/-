#!/usr/bin/env python3
"""
Pytest 测试配置文件
提供 Flask 测试客户端、临时文件数据库和 fixtures
"""

import sys
import os
import pytest
import sqlite3

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, socketio
from app.routes.main import hash_password

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test.db')

# ========== 数据库 Schema ==========
INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    name TEXT,
    phone TEXT,
    email TEXT,
    child_name TEXT,
    role TEXT DEFAULT 'user'
);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    total_hours INTEGER,
    price REAL,
    start_time TEXT,
    end_time TEXT,
    max_students INTEGER,
    current_students INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    course_id INTEGER,
    status TEXT DEFAULT 'pending',
    payment_amount REAL,
    payment_time TEXT,
    attendance_count INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE TABLE IF NOT EXISTS attendances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER,
    class_date TEXT,
    class_number INTEGER,
    status TEXT DEFAULT 'absent',
    FOREIGN KEY (enrollment_id) REFERENCES enrollments (id)
);

CREATE TABLE IF NOT EXISTS alternate_courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enrollment_id INTEGER,
    course_id INTEGER,
    status TEXT DEFAULT 'pending',
    FOREIGN KEY (enrollment_id) REFERENCES enrollments (id),
    FOREIGN KEY (course_id) REFERENCES courses (id)
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender_id INTEGER,
    receiver_id INTEGER,
    content TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'unread',
    FOREIGN KEY (sender_id) REFERENCES users (id),
    FOREIGN KEY (receiver_id) REFERENCES users (id)
);

CREATE TABLE IF NOT EXISTS chat_pins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    pinned_user_id INTEGER NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, pinned_user_id),
    FOREIGN KEY (user_id) REFERENCES users (id),
    FOREIGN KEY (pinned_user_id) REFERENCES users (id)
);
"""


def _init_test_db(db_path):
    """初始化测试数据库并插入测试数据"""
    # 删除旧数据库确保干净
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(INIT_SQL)
    cursor = conn.cursor()

    # 插入管理员
    admin_pw = hash_password('admin123')
    cursor.execute(
        "INSERT INTO users (username, password, name, phone, child_name, role) VALUES (?, ?, ?, ?, ?, ?)",
        ('admin', admin_pw, '管理员', '13800138000', '管理员孩子', 'admin')
    )
    admin_id = cursor.lastrowid

    # 插入普通用户（信息完整）
    user_pw = hash_password('user123')
    cursor.execute(
        "INSERT INTO users (username, password, name, phone, child_name, role) VALUES (?, ?, ?, ?, ?, ?)",
        ('user1', user_pw, '张家长', '13900139000', '张小明', 'user')
    )
    user1_id = cursor.lastrowid

    # 插入普通用户（信息不完整）
    cursor.execute(
        "INSERT INTO users (username, password, name, phone, child_name, role) VALUES (?, ?, ?, ?, ?, ?)",
        ('user2', user_pw, '未知', '13900139001', '未知', 'user')
    )
    user2_id = cursor.lastrowid

    # 插入课程（未满）
    cursor.execute(
        "INSERT INTO courses (name, description, total_hours, price, start_time, end_time, max_students, current_students) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('少儿毛笔基础班', '基础笔画学习', 24, 1280.0, '2026-03-01', '2026-06-15', 12, 2)
    )
    course1_id = cursor.lastrowid

    # 插入课程（已满）
    cursor.execute(
        "INSERT INTO courses (name, description, total_hours, price, start_time, end_time, max_students, current_students) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('硬笔规范字班', '规范字练习', 20, 980.0, '2026-03-08', '2026-06-08', 2, 2)
    )
    course2_id = cursor.lastrowid

    # 插入课程（有余量，用于调课目标）
    cursor.execute(
        "INSERT INTO courses (name, description, total_hours, price, start_time, end_time, max_students, current_students) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('行书提高班', '行书技法', 28, 1980.0, '2026-03-10', '2026-07-10', 8, 1)
    )
    course3_id = cursor.lastrowid

    # 插入报名记录
    cursor.execute(
        "INSERT INTO enrollments (user_id, course_id, status, payment_amount, attendance_count) VALUES (?, ?, ?, ?, ?)",
        (user1_id, course1_id, 'paid', 1280.0, 0)
    )
    enrollment1_id = cursor.lastrowid

    cursor.execute(
        "INSERT INTO enrollments (user_id, course_id, status, payment_amount, attendance_count) VALUES (?, ?, ?, ?, ?)",
        (user1_id, course2_id, 'paid', 980.0, 0)
    )

    conn.commit()
    conn.close()
    return {
        'admin_id': admin_id,
        'user1_id': user1_id,
        'user2_id': user2_id,
        'course1_id': course1_id,
        'course2_id': course2_id,
        'course3_id': course3_id,
        'enrollment1_id': enrollment1_id,
    }


@pytest.fixture(scope='function', autouse=True)
def setup_test_db():
    """函数级别：每个测试前初始化测试数据库"""
    test_data = _init_test_db(TEST_DB_PATH)
    yield test_data
    # 测试结束后清理
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture
def client(setup_test_db):
    """Flask 测试客户端 fixture，使用临时文件数据库"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key-12345'
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['WTF_CSRF_ENABLED'] = False

    # 替换数据库连接为测试数据库
    import app.routes.main as main_module
    # 清理频率限制全局状态
    main_module.request_limits.clear()
    original_db_path = main_module.db_path
    main_module.db_path = TEST_DB_PATH

    import app.models.database as db_module
    original_get_db = db_module.get_db_connection

    def _get_test_conn():
        conn = sqlite3.connect(TEST_DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    db_module.get_db_connection = _get_test_conn
    main_module.get_db_connection = _get_test_conn

    with app.test_client() as test_client:
        test_client.test_data = setup_test_db
        yield test_client

    # 恢复
    main_module.db_path = original_db_path
    db_module.get_db_connection = original_get_db
    main_module.get_db_connection = original_get_db


@pytest.fixture
def admin_logged_in(client):
    """已登录管理员的客户端 session"""
    with client.session_transaction() as sess:
        sess['user_id'] = client.test_data['admin_id']
        sess['username'] = 'admin'
        sess['role'] = 'admin'
        sess['profile_complete'] = True
    return client


@pytest.fixture
def user_logged_in(client):
    """已登录普通用户（信息完整）的客户端 session"""
    with client.session_transaction() as sess:
        sess['user_id'] = client.test_data['user1_id']
        sess['username'] = 'user1'
        sess['role'] = 'user'
        sess['profile_complete'] = True
    return client


@pytest.fixture
def incomplete_user_logged_in(client):
    """已登录信息不完整用户的客户端 session"""
    with client.session_transaction() as sess:
        sess['user_id'] = client.test_data['user2_id']
        sess['username'] = 'user2'
        sess['role'] = 'user'
    return client
