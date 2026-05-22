import sqlite3
import os

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
db_path = os.path.join(grandparent_dir, 'calligraphy_system.db')

# MySQL 配置（通过环境变量切换，未设置则默认使用 SQLite）
USE_MYSQL = os.environ.get('USE_MYSQL', 'false').lower() == 'true'
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', 'root'),
    'database': os.environ.get('MYSQL_DATABASE', 'calligraphy_system'),
    'charset': 'utf8mb4'
}


def _get_mysql_conn():
    """获取 MySQL 数据库连接（需要安装 pymysql）。"""
    import pymysql
    conn = pymysql.connect(
        host=MYSQL_CONFIG['host'],
        port=MYSQL_CONFIG['port'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )
    return conn


def _get_sqlite_conn():
    """获取 SQLite 数据库连接。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_db_connection():
    """根据配置获取对应的数据库连接（SQLite 或 MySQL）。"""
    if USE_MYSQL:
        return _get_mysql_conn()
    return _get_sqlite_conn()


class DatabaseConnection:
    """数据库连接上下文管理器，自动处理事务提交和连接关闭。"""
    
    def __enter__(self):
        self.conn = get_db_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()


def init_db():
    """初始化 SQLite 数据库（仅在 SQLite 模式下有效）。"""
    if USE_MYSQL:
        print('当前使用 MySQL 模式，跳过 SQLite 初始化')
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 启用 SQLite 外键约束，确保数据引用完整性
    cursor.execute('PRAGMA foreign_keys = ON')
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        phone TEXT,
        email TEXT,
        child_name TEXT,
        role TEXT DEFAULT 'user'
    )
    ''')
    
    # 创建课程表
    cursor.execute('''
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
    )
    ''')
    
    # 创建报名记录表
    cursor.execute('''
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
    )
    ''')
    
    # 创建签到记录表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER,
        class_date TEXT,
        class_number INTEGER,
        status TEXT DEFAULT 'absent',
        FOREIGN KEY (enrollment_id) REFERENCES enrollments (id)
    )
    ''')
    
    # 创建备选课程表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS alternate_courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        enrollment_id INTEGER,
        course_id INTEGER,
        status TEXT DEFAULT 'pending',
        FOREIGN KEY (enrollment_id) REFERENCES enrollments (id),
        FOREIGN KEY (course_id) REFERENCES courses (id)
    )
    ''')
    
    # 创建消息表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        receiver_id INTEGER,
        content TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'unread',
        FOREIGN KEY (sender_id) REFERENCES users (id),
        FOREIGN KEY (receiver_id) REFERENCES users (id)
    )
    ''')
    
    # 创建聊天置顶表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_pins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        pinned_user_id INTEGER NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, pinned_user_id),
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (pinned_user_id) REFERENCES users (id)
    )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print('数据库初始化完成')
