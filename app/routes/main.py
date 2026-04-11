from flask import render_template, request, jsonify, session, redirect, url_for, send_file
from flask_socketio import emit, join_room, leave_room
import sqlite3
import hashlib
import time
import os
import random
import secrets
import string
import re
import io
import base64
from datetime import datetime, timedelta
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
from app import app, socketio
from app.models.database import get_db_connection, DatabaseConnection

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
grandparent_dir = os.path.dirname(parent_dir)
db_path = os.path.join(grandparent_dir, 'calligraphy_system.db')

PHONE_PATTERN = re.compile(r'^1[3-9]\d{9}$')

def validate_phone(phone):
    """验证手机号是否符合中国大陆手机号格式（1开头，第二位3-9，共11位）。"""
    return bool(PHONE_PATTERN.match(phone))

# 配置Session安全
app.config.update(
    SESSION_COOKIE_SECURE=False,  # 本地开发使用HTTP，如需HTTPS生产环境请改为True
    SESSION_COOKIE_HTTPONLY=True,  # 防止JavaScript访问
    SESSION_COOKIE_SAMESITE='Lax',  # CSRF保护
    PERMANENT_SESSION_LIFETIME=timedelta(hours=2)  # Session过期时间
)

# 请求频率限制字典
request_limits = {}

# 中间件：检查用户信息是否完整
@app.before_request
def check_profile_completeness():
    """请求前中间件：检查已登录用户的个人信息是否完整，不完整则强制跳转完善页面。"""
    exempt_routes = ['login', 'register', 'send_verification_code', 'captcha', 'static', 'complete_profile', 'update_profile', 'logout']
    
    current_route = request.endpoint
    if current_route in exempt_routes:
        return None
    
    if 'user_id' in session:
        # 优先使用 session 中缓存的完整性状态
        if 'profile_complete' in session and not session['profile_complete']:
            return redirect(url_for('complete_profile'))
        
        # 如果 session 中没有缓存，查询数据库并缓存
        if 'profile_complete' not in session:
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
            conn.close()
            
            if user:
                profile_complete = not (user['name'] == '未知' or user['child_name'] == '未知' or not user['phone'])
                session['profile_complete'] = profile_complete
                if not profile_complete:
                    return redirect(url_for('complete_profile'))
    
    return None

# 数据库连接上下文管理器
class DatabaseConnection:
    def __enter__(self):
        """进入上下文时建立数据库连接。"""
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文时自动提交或回滚事务并关闭连接。"""
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

# 保留原函数以兼容现有代码
def get_db_connection():
    """获取sqlite3数据库连接，返回行工厂模式的结果集。"""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def get_admin_user(conn):
    """从数据库查询第一个管理员用户信息。"""
    return conn.execute(
        'SELECT id, username, name FROM users WHERE role = ? ORDER BY id LIMIT 1',
        ('admin',)
    ).fetchone()


def get_conversation_messages(conn, user_a, user_b):
    """查询两个用户之间的全部聊天记录，按时间正序排列。"""
    return conn.execute(
        '''
        SELECT m.*, sender.name AS sender_name, receiver.name AS receiver_name
        FROM messages m
        JOIN users sender ON sender.id = m.sender_id
        JOIN users receiver ON receiver.id = m.receiver_id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC, m.id ASC
        ''',
        (user_a, user_b, user_b, user_a)
    ).fetchall()

# 密码加密函数（使用pbkdf2）
def hash_password(password):
    """使用 PBKDF2-HMAC-SHA256 对密码进行哈希加密，返回 salt$hash 格式字符串。"""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000  # 迭代次数
    )
    return f'{salt}${key.hex()}'

# 验证密码函数
def verify_password(password, hashed_password):
    """验证密码与哈希值是否匹配，兼容旧版 SHA256 格式。"""
    try:
        if '$' in hashed_password:
            # PBKDF2-HMAC-SHA256 格式
            salt, key = hashed_password.split('$')
            new_key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return secrets.compare_digest(new_key.hex(), key)
        else:
            # 兼容旧版纯 SHA256 格式
            old_hash = hashlib.sha256(password.encode('utf-8')).hexdigest()
            return secrets.compare_digest(old_hash, hashed_password)
    except Exception:
        return False

# 请求频率限制装饰器
def rate_limit(max_requests=5, window=60):
    """请求频率限制装饰器，基于客户端IP限制指定时间窗口内的最大请求次数。"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取客户端IP
            client_ip = request.remote_addr
            current_time = time.time()
            
            # 清理过期记录
            if client_ip in request_limits:
                request_limits[client_ip] = [
                    (timestamp, count) for timestamp, count in request_limits[client_ip]
                    if current_time - timestamp < window
                ]
                if not request_limits[client_ip]:
                    del request_limits[client_ip]
            
            # 检查请求次数
            if client_ip not in request_limits:
                request_limits[client_ip] = []
            
            total_requests = sum(count for _, count in request_limits[client_ip])
            if total_requests >= max_requests:
                return jsonify({'success': False, 'message': '请求过于频繁，请稍后再试'}), 429
            
            # 记录请求
            request_limits[client_ip].append((current_time, 1))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def _create_captcha_image(captcha_text):
    """根据验证码文本生成干扰线/点的PNG图片，返回BytesIO对象。"""
    """创建验证码图片，返回 BytesIO 对象"""
    # 根据字符数动态计算宽度，避免字符被截断
    char_width = 32
    padding = 15
    width = max(120, len(captcha_text) * char_width + padding * 2)
    height = 40
    image = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    
    try:
        font = ImageFont.truetype('arial.ttf', 28)
    except:
        font = ImageFont.load_default()
    
    for i, char in enumerate(captcha_text):
        draw.text((padding + i * char_width, 5), char, font=font, fill=(random.randint(0, 100), random.randint(0, 100), random.randint(0, 100)))
    
    for _ in range(5):
        draw.line([(random.randint(0, width), random.randint(0, height)), (random.randint(0, width), random.randint(0, height))], fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))
    
    for _ in range(50):
        draw.point((random.randint(0, width), random.randint(0, height)), fill=(random.randint(100, 200), random.randint(100, 200), random.randint(100, 200)))
    
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

# 生成验证码
def generate_captcha(return_base64=True):
    """生成4位数字验证码图片，存储到Session，5分钟过期。"""
    chars = '23456789'
    captcha_text = ''.join(secrets.choice(chars) for _ in range(4))
    session['captcha'] = captcha_text
    session['captcha_created_at'] = time.time()
    
    buffer = _create_captcha_image(captcha_text)
    
    if return_base64:
        img_base64 = base64.b64encode(buffer.read()).decode('utf-8')
        return img_base64
    else:
        buffer.seek(0)
        return buffer

# 验证验证码
def check_captcha(user_input):
    """验证用户输入的验证码是否与Session中存储的一致，300秒过期。"""
    stored = session.get('captcha', '')
    created_at = session.get('captcha_created_at', 0)
    if not stored or not user_input:
        return False
    if time.time() - created_at > 300:
        return False
    return secrets.compare_digest(stored.lower(), user_input.lower())

# 路由：验证码
@app.route('/captcha')
def get_captcha():
    """验证码图片路由，返回PNG格式验证码图片。"""
    buffer = generate_captcha(return_base64=False)
    return send_file(buffer, mimetype='image/png')

# 初始化管理员账户
def init_admin():
    """初始化默认管理员账号（admin/admin123），不存在则创建，密码格式旧则升级。"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # 检查是否已有管理员账户
    cursor.execute('SELECT * FROM users WHERE role = ?', ('admin',))
    admin = cursor.fetchone()
    if not admin:
        # 创建默认管理员账户
        cursor.execute('''
        INSERT INTO users (username, password, name, phone, email, child_name, role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', ('admin', hash_password('admin123'), '管理员', '13800138000', 'admin@example.com', '管理员', 'admin'))
        conn.commit()
    else:
        # 如果现有管理员密码无法通过当前算法验证，则更新密码
        # 这通常发生在密码哈希算法升级后
        try:
            if not verify_password('admin123', admin['password']):
                cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password('admin123'), admin['id']))
                conn.commit()
                print('管理员密码已更新为当前加密格式')
        except Exception:
            cursor.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password('admin123'), admin['id']))
            conn.commit()
            print('管理员密码已更新为当前加密格式')
    conn.close()

# 路由：首页
@app.route('/')
def index():
    """系统首页路由，已登录用户展示个人信息，未登录跳转登录页。"""
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        conn.close()
        return render_template('index.html', user=user)
    return redirect(url_for('login'))

# 路由：登录
@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=5, window=60)  # 添加频率限制
def login():
    """用户登录路由，支持用户名密码和手机号验证码两种登录模式。"""
    if request.method == 'POST':
        # 检查是否是手机号验证码登录
        if 'phone' in request.form and 'verification_code' in request.form:
            phone = request.form.get('phone', '').strip()
            verification_code = request.form.get('verification_code', '').strip()
            
            # 验证验证码
            if 'verification_code' not in session:
                app.logger.warning(f'验证码不在session中: session_keys={list(session.keys())}, phone={phone}')
                return render_template('login.html', error='验证码未发送或已失效，请重新获取', phone=phone, mode='code')
            if verification_code != session['verification_code']:
                app.logger.warning(f'验证码不匹配: 输入="{verification_code}", session="{session.get("verification_code")}", phone={phone}')
                return render_template('login.html', error='验证码错误', phone=phone, mode='code')
            
            # 检查验证码是否过期（5分钟）
            code_created_at = session.get('verification_code_created_at', 0)
            if time.time() - code_created_at > 300:
                return render_template('login.html', error='验证码已过期', phone=phone, mode='code')
            
            if 'phone' not in session or phone != session['phone']:
                return render_template('login.html', error='手机号与验证码不匹配', phone=phone, mode='code')
            
            if not validate_phone(phone):
                return render_template('login.html', error='手机号格式不正确', phone=phone, mode='code')
            
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
            generated_password = None
            
            if not user:
                username = 'user_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
                characters = string.ascii_letters + string.digits + "!@#$%^&*()_+'-=[]{};:\\|,.<>/?"
                password = ''.join(secrets.choice(characters) for _ in range(12))
                generated_password = password
                
                conn.execute('''
                INSERT INTO users (username, password, name, phone, child_name)
                VALUES (?, ?, ?, ?, ?)
                ''', (username, hash_password(password), '未知', phone, '未知'))
                conn.commit()
                
                user = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
            
            conn.close()
            
            # 验证码使用后立即失效
            session.pop('verification_code', None)
            session.pop('verification_code_created_at', None)
            
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['name'] = user['name']
            session['role'] = user['role']
            session['profile_complete'] = not (user['name'] == '未知' or user['child_name'] == '未知' or not user['phone'])
            
            # 检查用户信息是否完整
            if not session['profile_complete']:
                # 保存生成的密码到session，用于完善信息后显示
                if generated_password:
                    session['generated_password'] = generated_password
                return redirect(url_for('complete_profile'))
            
            return redirect(url_for('index'))
        else:
            # 原有的用户名密码登录
            username = request.form['username']
            password = request.form['password']
            captcha = request.form['captcha']
            
            # 验证验证码
            if not check_captcha(captcha):
                return render_template('login.html', error='验证码错误或已过期')
            
            conn = get_db_connection()
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()
            
            if user and verify_password(password, user['password']):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['name'] = user['name']
                session['role'] = user['role']
                # 缓存个人信息完整性状态
                session['profile_complete'] = not (user['name'] == '未知' or user['child_name'] == '未知' or not user['phone'])
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='用户名或密码错误')
    # GET请求时，检查是否有生成的密码
    generated_password = session.pop('generated_password', None)
    return render_template('login.html', generated_password=generated_password)

# 路由：发送验证码（开发环境直接返回验证码，未接入短信服务）
@app.route('/send_verification_code', methods=['POST'])
def send_verification_code():
    """发送手机验证码路由（演示环境直接返回验证码），5分钟有效。"""
    phone = ((request.get_json() or {}).get('phone') or '').strip()
    if not phone:
        return jsonify({'success': False, 'message': '请输入手机号'})
    
    if not validate_phone(phone):
        return jsonify({'success': False, 'message': '手机号格式不正确'})
    
    verification_code = ''.join(secrets.choice('0123456789') for _ in range(6))
    session['verification_code'] = verification_code
    session['verification_code_created_at'] = time.time()
    session['phone'] = phone
    
    app.logger.info(f'生成验证码: phone={phone}, code={verification_code}')
    
    return jsonify({'success': True, 'message': '验证码已生成', 'verification_code': verification_code})

# 路由：注册
@app.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册路由，通过手机号验证码完成注册，自动生成随机账号密码。"""
    if request.method == 'POST':
        phone = request.form['phone']
        verification_code = request.form['verification_code']
        name = request.form['name']
        child_name = request.form['child_name']
        
        # 验证验证码
        if 'verification_code' not in session or verification_code != session['verification_code']:
            return render_template('register.html', error='验证码错误')
        
        # 检查验证码是否过期
        code_created_at = session.get('verification_code_created_at', 0)
        if time.time() - code_created_at > 300:
            return render_template('register.html', error='验证码已过期')
        
        if 'phone' not in session or phone != session['phone']:
            return render_template('register.html', error='手机号与验证码不匹配')
        
        if not validate_phone(phone):
            return render_template('register.html', error='手机号格式不正确')
        
        # 基础输入验证
        if not name or len(name) > 50:
            return render_template('register.html', error='姓名不能为空且不能超过50个字符')
        if not child_name or len(child_name) > 50:
            return render_template('register.html', error='孩子姓名不能为空且不能超过50个字符')
        
        conn = get_db_connection()
        # 检查手机号是否已存在
        existing_user = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
        if existing_user:
            conn.close()
            return render_template('register.html', error='手机号已注册')
        
        username = 'user_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        characters = string.ascii_letters + string.digits + "!@#$%^&*()_+'-=[]{};:,.<>/?.'"
        password = ''.join(secrets.choice(characters) for _ in range(12))
        
        # 创建新用户
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (username, password, name, phone, child_name)
        VALUES (?, ?, ?, ?, ?)
        ''', (username, hash_password(password), name, phone, child_name))
        user_id = cursor.lastrowid
        conn.commit()
        
        # 保存生成的账号密码到session，用于注册成功后显示
        session['generated_username'] = username
        session['generated_password'] = password
        
        # 登录用户
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['profile_complete'] = True
        
        # 验证码使用后立即失效
        session.pop('verification_code', None)
        session.pop('verification_code_created_at', None)
        
        conn.close()
        
        return redirect(url_for('register_success'))
    return render_template('register.html')

# 路由：完善个人信息
@app.route('/complete_profile', methods=['GET', 'POST'])
def complete_profile():
    """完善个人信息路由，强制用户补充姓名、孩子姓名和手机号。"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if request.method == 'POST':
        name = request.form['name']
        child_name = request.form['child_name']
        phone = request.form['phone']
        
        if not name or len(name) > 50:
            conn.close()
            return render_template('complete_profile.html', user=user, error='姓名不能为空且不能超过50个字符')
        if not child_name or len(child_name) > 50:
            conn.close()
            return render_template('complete_profile.html', user=user, error='孩子姓名不能为空且不能超过50个字符')
        if not validate_phone(phone):
            conn.close()
            return render_template('complete_profile.html', user=user, error='手机号格式不正确')
        
        # 更新用户信息
        conn.execute('''
        UPDATE users 
        SET name = ?, child_name = ?, phone = ? 
        WHERE id = ?
        ''', (name, child_name, phone, session['user_id']))
        conn.commit()
        conn.close()
        
        session['profile_complete'] = True
        return redirect(url_for('index'))
    
    conn.close()
    return render_template('complete_profile.html', user=user)

# 路由：更新个人信息
@app.route('/update_profile', methods=['POST'])
def update_profile():
    """AJAX接口：更新当前登录用户的个人信息。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    data = request.get_json() or {}
    name = data.get('name')
    child_name = data.get('child_name')
    phone = data.get('phone')
    
    if not name or not child_name or not phone:
        return jsonify({'success': False, 'message': '请填写完整的个人信息'})
    
    if not name or len(name) > 50:
        return jsonify({'success': False, 'message': '姓名不能为空且不能超过50个字符'})
    if not child_name or len(child_name) > 50:
        return jsonify({'success': False, 'message': '孩子姓名不能为空且不能超过50个字符'})
    if not validate_phone(phone):
        return jsonify({'success': False, 'message': '手机号格式不正确'})
    
    conn = get_db_connection()
    # 更新用户信息
    conn.execute('''
    UPDATE users 
    SET name = ?, child_name = ?, phone = ? 
    WHERE id = ?
    ''', (name, child_name, phone, session['user_id']))
    conn.commit()
    conn.close()
    
    session['profile_complete'] = True
    session['name'] = name
    return jsonify({'success': True, 'message': '个人信息更新成功'})

# 路由：注册成功
@app.route('/register_success')
def register_success():
    """注册成功展示页，显示系统生成的随机用户名和密码。"""
    if 'generated_username' not in session:
        return redirect(url_for('register'))
    
    username = session.pop('generated_username')
    password = session.pop('generated_password', None)
    
    return render_template('register_success.html', username=username, password=password)

# 路由：注销
@app.route('/logout')
def logout():
    """用户登出路由，清除全部Session数据。"""
    session.clear()
    return redirect(url_for('login'))

# 路由：用户中心
@app.route('/user_center')
def user_center():
    """用户中心路由，展示个人信息和报名记录。"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    # 获取用户的报名记录
    enrollments = conn.execute('''
    SELECT e.id, c.name as course_name, c.name as class_name, c.start_time, c.end_time, e.status
    FROM enrollments e
    JOIN courses c ON e.course_id = c.id
    WHERE e.user_id = ?
    ''', (session['user_id'],)).fetchall()
    conn.close()
    
    return render_template('user_center.html', user=user, enrollments=enrollments)

# 路由：课程列表
@app.route('/courses')
def courses():
    """课程列表路由，展示所有课程信息。"""
    conn = get_db_connection()
    courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    return render_template('courses.html', courses=courses)

# 路由：课程详情
@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """课程详情路由，管理员可见全部及报名学生，普通用户仅见未满课程。"""
    conn = get_db_connection()
    # 对于管理员，显示所有课程（包括已满的）
    if 'role' in session and session['role'] == 'admin':
        course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    else:
        # 对于普通用户，只显示未满的课程
        course = conn.execute('SELECT * FROM courses WHERE id = ? AND current_students < max_students', (course_id,)).fetchone()
    
    # 获取所有课程列表（用于备选课程选择）
    all_courses = conn.execute('SELECT * FROM courses').fetchall()
    
    # 获取报名学生列表（仅管理员）
    enrolled_students = []
    user_enrollment = None
    if 'role' in session and session['role'] == 'admin' and course:
        # 获取所有报名记录
        enrollments = conn.execute('''
        SELECT u.*, e.id as enrollment_id, e.status 
        FROM users u
        JOIN enrollments e ON u.id = e.user_id
        WHERE e.course_id = ?
        ''', (course_id,)).fetchall()
        
        # 为每个学生添加是否有备选课程的标记
        for student in enrollments:
            # 检查是否有备选课程
            has_alternate = conn.execute('''
            SELECT COUNT(*) FROM alternate_courses 
            WHERE enrollment_id = ?
            ''', (student['enrollment_id'],)).fetchone()[0] > 0
            # 将has_alternate添加到学生字典中
            student_dict = dict(student)
            student_dict['has_alternate'] = has_alternate
            enrolled_students.append(student_dict)

    if 'user_id' in session and session.get('role') != 'admin' and course:
        user_enrollment = conn.execute(
            '''
            SELECT e.*, COUNT(ac.id) AS alternate_count
            FROM enrollments e
            LEFT JOIN alternate_courses ac ON ac.enrollment_id = e.id
            WHERE e.user_id = ? AND e.course_id = ?
            GROUP BY e.id
            ''',
            (session['user_id'], course_id)
        ).fetchone()
    
    conn.close()
    
    return render_template(
        'course_detail.html',
        course=course,
        all_courses=all_courses,
        enrolled_students=enrolled_students,
        user_enrollment=user_enrollment
    )

# 路由：报名课程
@app.route('/enroll/<int:course_id>', methods=['POST'])
def enroll(course_id):
    """课程报名路由，校验信息完整性、课程余量、重复报名后保存报名意向到Session。"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 检查用户信息是否完整
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if user['name'] == '未知' or user['child_name'] == '未知' or not user['phone']:
        conn.close()
        return jsonify({'success': False, 'message': '请先完善个人信息'})
    
    # 检查课程是否存在且未满
    course = conn.execute('''
    SELECT * FROM courses 
    WHERE id = ? AND current_students < max_students
    ''', (course_id,)).fetchone()
    
    if not course:
        conn.close()
        return jsonify({'success': False, 'message': '课程不存在或已满'})
    
    # 检查用户是否已报名该课程
    existing_enrollment = conn.execute('''
    SELECT * FROM enrollments 
    WHERE user_id = ? AND course_id = ?
    ''', (session['user_id'], course_id)).fetchone()
    
    if existing_enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '您已报名该课程'})
    
    conn.close()
    
    # 保存课程信息到session，用于缴费后创建报名记录
    session['course_id'] = course_id
    data = request.get_json() or {}
    session['alternate_courses'] = data.get('alternate_courses', [])
    
    return jsonify({'success': True, 'message': '请先完成缴费'})

# 路由：缴费
@app.route('/payment', methods=['POST'])
def payment():
    """模拟缴费路由，使用数据库事务创建报名记录、备选课程，更新课程人数。"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 检查是否有课程信息在session中
    if 'course_id' not in session:
        return jsonify({'success': False, 'message': '请先选择课程'})
    
    course_id = session['course_id']
    alternate_courses = session.get('alternate_courses', [])
    
    conn = get_db_connection()
    
    # 检查课程是否存在且未满
    course = conn.execute('''
    SELECT * FROM courses 
    WHERE id = ? AND current_students < max_students
    ''', (course_id,)).fetchone()
    
    if not course:
        conn.close()
        return jsonify({'success': False, 'message': '课程不存在或已满'})
    
    # 检查用户是否已报名该课程
    existing_enrollment = conn.execute('''
    SELECT * FROM enrollments 
    WHERE user_id = ? AND course_id = ?
    ''', (session['user_id'], course_id)).fetchone()
    
    if existing_enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '您已报名该课程'})
    
    # 模拟缴费验证过程
    # 在实际应用中，这里应该集成支付平台的回调验证
    payment_verified = True  # 假设缴费成功
    
    if payment_verified:
        # 开始事务
        conn.execute('BEGIN TRANSACTION')
        
        try:
            # 创建报名记录
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO enrollments (user_id, course_id, status, payment_amount, payment_time)
            VALUES (?, ?, ?, ?, ?)
            ''', (session['user_id'], course_id, 'paid', course['price'], time.strftime('%Y-%m-%d %H:%M:%S')))
            enrollment_id = cursor.lastrowid
            
            # 处理备选课程
            for alt_course_id in alternate_courses:
                # 检查备选课程是否存在
                alt_course = conn.execute('SELECT * FROM courses WHERE id = ?', (alt_course_id,)).fetchone()
                if alt_course:
                    conn.execute('''
                    INSERT INTO alternate_courses (enrollment_id, course_id, status)
                    VALUES (?, ?, ?)
                    ''', (enrollment_id, alt_course_id, 'pending'))
            
            # 更新课程的当前人数
            conn.execute('''
            UPDATE courses 
            SET current_students = current_students + 1 
            WHERE id = ?
            ''', (course_id,))
            
            conn.commit()
            conn.close()
            
            # 清除session中的课程信息
            session.pop('course_id', None)
            session.pop('alternate_courses', None)
            
            return jsonify({'success': True, 'message': '缴费成功，报名已完成'})
        except Exception as e:
            conn.rollback()
            conn.close()
            return jsonify({'success': False, 'message': '缴费失败，请重试'})
    else:
        conn.close()
        return jsonify({'success': False, 'message': '缴费验证失败，请重试'})

# 路由：管理员后台
@app.route('/admin')
def admin():
    """管理员后台路由，展示所有课程列表。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # 获取所有课程
    courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    
    return render_template('admin.html', courses=courses)

# 路由：添加课程
@app.route('/admin/add_course', methods=['POST'])
def add_course():
    """管理员添加课程路由，校验输入后插入数据库。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    start_time = request.form.get('start_time', '').strip()
    end_time = request.form.get('end_time', '').strip()
    
    try:
        total_hours = int(request.form['total_hours'])
        price = float(request.form['price'])
        max_students = int(request.form['max_students'])
    except (KeyError, ValueError):
        return redirect(url_for('admin'))
    
    if not name or len(name) > 100:
        return redirect(url_for('admin'))
    if not start_time or not end_time:
        return redirect(url_for('admin'))
    if total_hours <= 0 or price < 0 or max_students <= 0:
        return redirect(url_for('admin'))
    
    conn = get_db_connection()
    conn.execute('''
    INSERT INTO courses (name, description, total_hours, price, start_time, end_time, max_students)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (name, description, total_hours, price, start_time, end_time, max_students))
    conn.commit()
    conn.close()
    
    return redirect(url_for('admin'))

# 路由：课程详情（管理员）
@app.route('/admin/course/<int:course_id>')
def admin_course(course_id):
    """管理员课程详情路由，展示报名学生列表及操作选项。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    # 获取URL参数中的student_id
    student_id = request.args.get('student_id', type=int)
    
    conn = get_db_connection()
    # 获取课程信息
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    # 获取该课程的报名学生
    students = conn.execute('''
    SELECT u.*, e.id as enrollment_id, e.status 
    FROM users u
    JOIN enrollments e ON u.id = e.user_id
    WHERE e.course_id = ?
    ''', (course_id,)).fetchall()
    
    # 获取所有课程列表（用于人员调整）
    all_courses = conn.execute('SELECT * FROM courses').fetchall()
    conn.close()
    
    return render_template('admin_class_session.html', class_session=course, students=students, all_courses=all_courses, student_id=student_id)

# 路由：签到
@app.route('/admin/attendance/<int:course_id>', methods=['GET', 'POST'])
def attendance(course_id):
    """管理员签到路由，GET渲染签到页，POST提交出勤状态并自动计算课时。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # 获取课程信息
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    
    # 计算是第几次课
    # 获取该课程的签到记录数量，加1就是本次课程的次数
    class_number = conn.execute('''
    SELECT COUNT(DISTINCT class_date) + 1 FROM attendances 
    JOIN enrollments ON attendances.enrollment_id = enrollments.id
    WHERE enrollments.course_id = ?
    ''', (course_id,)).fetchone()[0]
    
    # 获取该课程的报名学生
    students = conn.execute('''
    SELECT u.*, e.id as enrollment_id 
    FROM users u
    JOIN enrollments e ON u.id = e.user_id
    WHERE e.course_id = ? AND e.status = 'paid'
    ''', (course_id,)).fetchall()
    
    if request.method == 'POST':
        class_date = request.form['class_date']
        
        # 处理签到记录
        for student in students:
            enrollment_id = student['enrollment_id']
            status = request.form.get(f'attendance_{enrollment_id}', 'absent')
            
            # 检查是否已有当天的签到记录
            existing_attendance = conn.execute('''
            SELECT * FROM attendances 
            WHERE enrollment_id = ? AND class_date = ?
            ''', (enrollment_id, class_date)).fetchone()
            
            old_status = existing_attendance['status'] if existing_attendance else None
            
            if existing_attendance:
                # 更新签到记录
                conn.execute('''
                UPDATE attendances 
                SET status = ?, class_number = ? 
                WHERE id = ?
                ''', (status, class_number, existing_attendance['id']))
            else:
                # 创建新的签到记录
                conn.execute('''
                INSERT INTO attendances (enrollment_id, class_date, class_number, status)
                VALUES (?, ?, ?, ?)
                ''', (enrollment_id, class_date, class_number, status))
            
            # 根据签到状态变化更新报名记录的签到次数
            if old_status != status:
                if old_status != 'present' and status == 'present':
                    conn.execute('''
                    UPDATE enrollments 
                    SET attendance_count = attendance_count + 1 
                    WHERE id = ?
                    ''', (enrollment_id,))
                elif old_status == 'present' and status != 'present':
                    conn.execute('''
                    UPDATE enrollments 
                    SET attendance_count = attendance_count - 1 
                    WHERE id = ?
                    ''', (enrollment_id,))
        
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))
    
    conn.close()
    return render_template('attendance.html', class_session=course, students=students, class_number=class_number)

# 路由：消息中心
@app.route('/messages')
def messages():
    """消息中心路由，管理员显示所有用户，普通用户显示管理员联系人。"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    # 如果是管理员，获取所有用户列表；普通用户只显示管理员为联系人
    users = []
    admin_user = None
    if session.get('role') == 'admin':
        users = conn.execute('SELECT id, name FROM users WHERE role = ? ORDER BY id DESC', ('user',)).fetchall()
    else:
        admin_user = get_admin_user(conn)
    conn.close()
    
    return render_template('messages.html', users=users, admin_user=admin_user)


@app.route('/api/conversation/<int:other_user_id>')
def api_conversation(other_user_id):
    """获取与指定用户的真实聊天记录，并将对方发来的未读消息标记为已读。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    current_user_id = int(session['user_id'])
    role = session.get('role', 'user')
    
    with DatabaseConnection() as conn:
        # 普通用户只能与管理员聊天：other_user_id 必须是管理员
        if role != 'admin':
            admin = get_admin_user(conn)
            if not admin or int(admin['id']) != int(other_user_id):
                return jsonify({'success': False, 'message': '无权限访问该会话'}), 403
        
        # 标记未读为已读（只标记对方 -> 当前用户 的消息）
        conn.execute(
            '''
            UPDATE messages
            SET status = 'read'
            WHERE receiver_id = ? AND sender_id = ? AND status = 'unread'
            ''',
            (current_user_id, int(other_user_id))
        )
        
        rows = get_conversation_messages(conn, current_user_id, int(other_user_id))
        
        messages = []
        for r in rows:
            messages.append({
                'id': r['id'],
                'sender_id': r['sender_id'],
                'receiver_id': r['receiver_id'],
                'content': r['content'] or '',
                'created_at': r['created_at'],
                'status': r['status'],
                'sender_name': r['sender_name'],
                'receiver_name': r['receiver_name'],
            })
        
        return jsonify({'success': True, 'messages': messages})

# 路由：发送消息
@app.route('/send_message', methods=['POST'])
def send_message():
    """发送消息路由，将消息持久化到数据库。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        receiver_id = int(request.form['receiver_id'])
    except (KeyError, ValueError):
        return jsonify({'success': False, 'message': '接收人ID无效'})
    content = (request.form.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'message': '消息内容不能为空'})
    if len(content) > 500:
        return jsonify({'success': False, 'message': '消息内容不能超过500个字符'})
    
    conn = get_db_connection()
    # 简单校验接收者是否存在
    receiver = conn.execute('SELECT id FROM users WHERE id = ?', (receiver_id,)).fetchone()
    if not receiver:
        conn.close()
        return jsonify({'success': False, 'message': '接收人不存在'})
    conn.execute('''
    INSERT INTO messages (sender_id, receiver_id, content)
    VALUES (?, ?, ?)
    ''', (session['user_id'], receiver_id, content))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '消息发送成功'})

# 路由：修改密码
@app.route('/change_password', methods=['POST'])
def change_password():
    """AJAX接口：修改当前用户密码，需验证原密码。"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    data = request.get_json() or {}
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码长度不能少于6位'})
    
    conn = get_db_connection()
    # 检查原密码是否正确
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not user or not verify_password(old_password, user['password']):
        conn.close()
        return jsonify({'success': False, 'message': '原密码错误'})
    
    # 更新密码
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hash_password(new_password), session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': '密码修改成功'})

# 路由：调整学生到其他课程
@app.route('/move_student', methods=['POST'])
def move_student():
    """AJAX接口：管理员将学员从当前课程调整至目标课程。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'})
    
    data = request.get_json() or {}
    student_id = data.get('student_id')
    current_course_id = data.get('current_course_id')
    target_course_id = data.get('target_course_id')
    
    conn = get_db_connection()
    
    # 检查目标课程是否存在且未满
    target_course = conn.execute('''
    SELECT * FROM courses 
    WHERE id = ? AND current_students < max_students
    ''', (target_course_id,)).fetchone()
    
    if not target_course:
        conn.close()
        return jsonify({'success': False, 'message': '目标课程不存在或已满'})
    
    # 检查学生是否在当前课程中
    enrollment = conn.execute('''
    SELECT * FROM enrollments 
    WHERE user_id = ? AND course_id = ?
    ''', (student_id, current_course_id)).fetchone()
    
    if not enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '学生不在当前课程中'})
    
    # 检查学生是否已在目标课程中
    existing_enrollment = conn.execute('''
    SELECT * FROM enrollments 
    WHERE user_id = ? AND course_id = ?
    ''', (student_id, target_course_id)).fetchone()
    
    if existing_enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '学生已在目标课程中'})
    
    # 开始事务
    conn.execute('BEGIN TRANSACTION')
    
    try:
        # 更新当前课程的人数
        conn.execute('''
        UPDATE courses 
        SET current_students = current_students - 1 
        WHERE id = ?
        ''', (current_course_id,))
        
        # 更新目标课程的人数
        conn.execute('''
        UPDATE courses 
        SET current_students = current_students + 1 
        WHERE id = ?
        ''', (target_course_id,))
        
        # 更新报名记录
        conn.execute('''
        UPDATE enrollments 
        SET course_id = ? 
        WHERE id = ?
        ''', (target_course_id, enrollment['id']))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '学生调整成功'})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': '调整失败，请重试'})

# 路由：移除学生
@app.route('/remove_student', methods=['POST'])
def remove_student():
    """AJAX接口：管理员移除学员报名记录及相关签到数据。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'})
    
    data = request.get_json() or {}
    enrollment_id = data.get('enrollment_id')
    
    conn = get_db_connection()
    
    # 获取报名记录
    enrollment = conn.execute('SELECT * FROM enrollments WHERE id = ?', (enrollment_id,)).fetchone()
    
    if not enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '报名记录不存在'})
    
    # 开始事务
    conn.execute('BEGIN TRANSACTION')
    
    try:
        # 更新课程人数
        conn.execute('''
        UPDATE courses 
        SET current_students = current_students - 1 
        WHERE id = ?
        ''', (enrollment['course_id'],))
        
        # 删除相关的签到记录
        conn.execute('DELETE FROM attendances WHERE enrollment_id = ?', (enrollment_id,))
        
        # 删除报名记录
        conn.execute('DELETE FROM enrollments WHERE id = ?', (enrollment_id,))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '学生移除成功'})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': '移除失败，请重试'})

# 路由：添加学生
@app.route('/add_student', methods=['POST'])
def add_student():
    """AJAX接口：管理员手动添加学员（无需注册），创建待缴费报名记录。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'})
    
    data = request.get_json() or {}
    course_id = data.get('course_id')
    child_name = data.get('child_name')
    parent_name = data.get('parent_name', '未知')
    phone = data.get('phone', '未知')
    
    if not course_id or not child_name:
        return jsonify({'success': False, 'message': '学生姓名为必填项'})
    
    conn = get_db_connection()
    
    # 检查课程是否存在
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        return jsonify({'success': False, 'message': '课程不存在'})
    
    # 检查课程是否已满
    if course['current_students'] >= course['max_students']:
        conn.close()
        return jsonify({'success': False, 'message': '课程已满'})
    
    # 开始事务
    conn.execute('BEGIN TRANSACTION')
    
    try:
        username = 'temp_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        characters = string.ascii_letters + string.digits + "!@#$%^&*()_+'-=[]{};:,.<>/?.'"
        password = ''.join(secrets.choice(characters) for _ in range(12))
        
        # 插入用户记录
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO users (username, password, name, phone, child_name, role)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, hash_password(password), parent_name, phone, child_name, 'user'))
        user_id = cursor.lastrowid
        
        # 创建报名记录，状态为待缴费
        cursor.execute('''
        INSERT INTO enrollments (user_id, course_id, status, payment_amount)
        VALUES (?, ?, ?, ?)
        ''', (user_id, course_id, 'pending', 0))
        
        # 更新课程人数
        conn.execute('''
        UPDATE courses 
        SET current_students = current_students + 1 
        WHERE id = ?
        ''', (course_id,))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '学生添加成功'})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': '添加失败，请重试'})

# 路由：课时管理
@app.route('/admin/hours_management')
def hours_management():
    """课时管理路由，统计各课程学员课时，标记低于平均课时的学员。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # 获取所有课程
    courses = conn.execute('SELECT * FROM courses').fetchall()
    
    # 获取每个课程的学生及其课时
    course_students = {}
    for course in courses:
        # 获取该课程的所有学生
        students = conn.execute('''
        SELECT u.*, e.id as enrollment_id, e.attendance_count 
        FROM users u
        JOIN enrollments e ON u.id = e.user_id
        WHERE e.course_id = ?
        ORDER BY e.attendance_count ASC
        ''', (course['id'],)).fetchall()
        
        if students:
            # 计算该课程的平均课时
            total_hours = sum(student['attendance_count'] for student in students)
            avg_hours = total_hours / len(students)
            
            # 标记课时低于平均值的学生并计算缺口
            for student in students:
                student_dict = dict(student)
                student_dict['below_average'] = student_dict['attendance_count'] < avg_hours
                if student_dict['below_average']:
                    student_dict['hours_gap'] = round(avg_hours - student_dict['attendance_count'])
                else:
                    student_dict['hours_gap'] = 0
                course_students.setdefault(course['id'], []).append(student_dict)
    
    conn.close()
    
    return render_template('hours_management.html', courses=courses, course_students=course_students)

# 路由：临时调课
@app.route('/temp_adjust', methods=['POST'])
def temp_adjust():
    """AJAX接口：管理员为学员添加临时调课签到记录。"""
    if 'user_id' not in session or session['role'] != 'admin':
        return jsonify({'success': False, 'message': '权限不足'})
    
    data = request.get_json() or {}
    enrollment_id = data.get('enrollment_id')
    course_id = data.get('course_id')
    class_date = data.get('class_date')
    
    if not enrollment_id or not course_id or not class_date:
        return jsonify({'success': False, 'message': '请填写完整的调课信息'})
    
    conn = get_db_connection()
    
    # 检查报名记录是否存在
    enrollment = conn.execute('SELECT * FROM enrollments WHERE id = ?', (enrollment_id,)).fetchone()
    if not enrollment:
        conn.close()
        return jsonify({'success': False, 'message': '报名记录不存在'})
    
    # 检查课程是否存在
    course = conn.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
    if not course:
        conn.close()
        return jsonify({'success': False, 'message': '课程不存在'})
    
    # 计算该课程的上课次数
    class_number = conn.execute('''
    SELECT COUNT(DISTINCT class_date) + 1 FROM attendances 
    JOIN enrollments ON attendances.enrollment_id = enrollments.id
    WHERE enrollments.course_id = ?
    ''', (course_id,)).fetchone()[0]
    
    # 开始事务
    conn.execute('BEGIN TRANSACTION')
    
    try:
        # 创建临时签到记录
        conn.execute('''
        INSERT INTO attendances (enrollment_id, class_date, class_number, status)
        VALUES (?, ?, ?, ?)
        ''', (enrollment_id, class_date, class_number, 'present'))
        
        # 更新报名记录的签到次数
        conn.execute('''
        UPDATE enrollments 
        SET attendance_count = attendance_count + 1 
        WHERE id = ?
        ''', (enrollment_id,))
        
        conn.commit()
        conn.close()
        
        # 通过WebSocket广播调课成功消息
        socketio.emit('temp_adjust_success', {
            'enrollment_id': enrollment_id,
            'course_id': course_id,
            'class_date': class_date,
            'message': '临时调课成功'
        }, room='admin')
        
        return jsonify({'success': True, 'message': '临时调课成功'})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({'success': False, 'message': '调课失败，请重试'})

# ========== WebSocket事件处理 ==========

@socketio.on('connect')
def handle_connect():
    """处理客户端连接"""
    if 'user_id' in session:
        user_id = session['user_id']
        username = session.get('username', '未知用户')
        role = session.get('role', 'user')
        
        # 加入用户专属房间
        join_room(f'user_{user_id}')
        
        # 如果是管理员，加入管理员房间
        if role == 'admin':
            join_room('admin')
        
        emit('connected', {
            'message': f'欢迎 {username} 连接成功！',
            'user_id': user_id,
            'role': role
        })
        print(f'用户 {username} (ID: {user_id}, 角色: {role}) 已连接')
    else:
        # 未登录用户，拒绝连接
        return False

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket事件：处理客户端断开连接。"""
    """处理客户端断开连接"""
    if 'user_id' in session:
        user_id = session['user_id']
        username = session.get('username', '未知用户')
        print(f'用户 {username} (ID: {user_id}) 已断开连接')

@socketio.on('join_course')
def handle_join_course(data):
    """加入课程房间"""
    if 'user_id' not in session:
        emit('error', {'message': '请先登录'})
        return
    
    course_id = data.get('course_id')
    if not course_id:
        emit('error', {'message': '课程ID不能为空'})
        return
    
    # 加入课程房间
    room_name = f'course_{course_id}'
    join_room(room_name)
    
    emit('joined_course', {
        'message': f'已加入课程 {course_id} 的房间',
        'course_id': course_id
    })

@socketio.on('leave_course')
def handle_leave_course(data):
    """离开课程房间"""
    if 'user_id' not in session:
        emit('error', {'message': '请先登录'})
        return
    
    course_id = data.get('course_id')
    if not course_id:
        emit('error', {'message': '课程ID不能为空'})
        return
    
    # 离开课程房间
    room_name = f'course_{course_id}'
    leave_room(room_name)
    
    emit('left_course', {
        'message': f'已离开课程 {course_id} 的房间',
        'course_id': course_id
    })

@socketio.on('send_message')
def handle_send_message(data):
    """发送消息到指定房间"""
    if 'user_id' not in session:
        emit('error', {'message': '请先登录'})
        return
    
    message = data.get('message', '').strip()
    room = data.get('room', 'general')  # 默认发送到general房间
    
    if not message:
        emit('error', {'message': '消息内容不能为空'})
        return
    
    if len(message) > 500:
        emit('error', {'message': '消息内容不能超过500个字符'})
        return
    
    # 只允许特定房间名格式
    allowed_rooms = {'general', 'admin'}
    if room.startswith('course_'):
        try:
            int(room.replace('course_', ''))
            allowed_rooms.add(room)
        except ValueError:
            pass
    if room.startswith('user_'):
        try:
            int(room.replace('user_', ''))
            allowed_rooms.add(room)
        except ValueError:
            pass
    
    if room not in allowed_rooms:
        emit('error', {'message': '无效的房间名'})
        return
    
    user_id = session['user_id']
    username = session.get('username', '未知用户')
    role = session.get('role', 'user')
    
    # 广播消息到指定房间
    emit('new_message', {
        'message': message,
        'user_id': user_id,
        'username': username,
        'role': role,
        'room': room,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }, room=room)
    
    print(f'用户 {username} 在房间 {room} 发送消息: {message}')

@socketio.on('attendance_update')
def handle_attendance_update(data):
    """签到更新通知"""
    if 'user_id' not in session or session['role'] != 'admin':
        emit('error', {'message': '权限不足'})
        return
    
    course_id = data.get('course_id')
    student_id = data.get('student_id')
    status = data.get('status')
    
    if not all([course_id, student_id, status]):
        emit('error', {'message': '参数不完整'})
        return
    
    # 广播签到更新到课程房间
    room_name = f'course_{course_id}'
    emit('attendance_changed', {
        'course_id': course_id,
        'student_id': student_id,
        'status': status,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }, room=room_name)

@socketio.on('course_enrollment')
def handle_course_enrollment(data):
    """课程报名通知"""
    if 'user_id' not in session:
        emit('error', {'message': '请先登录'})
        return
    
    course_id = data.get('course_id')
    user_id = session['user_id']
    username = session.get('username', '未知用户')
    
    # 广播报名信息到管理员房间
    emit('new_enrollment', {
        'course_id': course_id,
        'user_id': user_id,
        'username': username,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    }, room='admin')

# ========== 全局错误处理 ==========

import logging

# 配置日志
if not app.debug:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('app.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

@app.errorhandler(404)
def not_found(error):
    """404错误处理：API请求返回JSON，页面请求渲染登录页。"""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '请求的资源不存在'}), 404
    return render_template('login.html', error='页面不存在'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理：记录异常日志，返回友好的错误提示。"""
    logging.error(f'服务器内部错误: {error}', exc_info=True)
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '服务器内部错误，请稍后重试'}), 500
    return render_template('login.html', error='服务器内部错误，请稍后重试'), 500

@app.errorhandler(429)
def rate_limit_handler(error):
    """429错误处理：请求过于频繁时的统一响应。"""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': '请求过于频繁，请稍后再试'}), 429
    return render_template('login.html', error='请求过于频繁，请稍后再试'), 429
