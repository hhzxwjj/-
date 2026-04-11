#!/usr/bin/env python3
"""生成测试数据：6个课程，约30名学员"""

import sqlite3
import random
import string
import secrets
import os
import sys

# 将 app 目录加入路径以导入 hash_password
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.routes.main import hash_password

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calligraphy_system.db')

courses_data = [
    {
        'name': '少儿毛笔书法基础班',
        'description': '面向零基础儿童，学习基本笔画和简单汉字书写，培养书法兴趣。',
        'total_hours': 24,
        'price': 1280.0,
        'start_time': '2026-03-01',
        'end_time': '2026-06-15',
        'max_students': 12
    },
    {
        'name': '少儿毛笔书法进阶班',
        'description': '在基础班之上，学习楷书结构和章法，完成简单作品创作。',
        'total_hours': 32,
        'price': 1680.0,
        'start_time': '2026-03-01',
        'end_time': '2026-06-30',
        'max_students': 10
    },
    {
        'name': '硬笔书法规范字班',
        'description': '针对小学生日常书写，纠正握笔姿势，练习规范楷书。',
        'total_hours': 20,
        'price': 980.0,
        'start_time': '2026-03-08',
        'end_time': '2026-06-08',
        'max_students': 15
    },
    {
        'name': '成人毛笔书法入门班',
        'description': '面向成人书法爱好者，从执笔、运笔开始，体验传统书法魅力。',
        'total_hours': 16,
        'price': 1080.0,
        'start_time': '2026-03-05',
        'end_time': '2026-05-25',
        'max_students': 10
    },
    {
        'name': '行书技法提高班',
        'description': '适合有一定基础者，系统学习行书笔法和结构，提升书写流畅度。',
        'total_hours': 28,
        'price': 1980.0,
        'start_time': '2026-03-10',
        'end_time': '2026-07-10',
        'max_students': 8
    },
    {
        'name': '书法考级冲刺班',
        'description': '针对书法等级考试进行专项训练，强化临摹和创作能力。',
        'total_hours': 20,
        'price': 1580.0,
        'start_time': '2026-04-01',
        'end_time': '2026-06-01',
        'max_students': 10
    }
]

student_names = [
    ('王伟', '王小伟'), ('李娜', '李小娜'), ('张强', '张小强'), ('刘洋', '刘小洋'),
    ('陈静', '陈小静'), ('杨帆', '杨小帆'), ('赵敏', '赵小敏'), ('黄磊', '黄小磊'),
    ('周杰', '周小杰'), ('吴婷', '吴小婷'), ('徐鹏', '徐小鹏'), ('孙丽', '孙小丽'),
    ('马超', '马小超'), ('朱琳', '朱小琳'), ('胡军', '胡小军'), ('郭欣', '郭小欣'),
    ('林峰', '林小峰'), ('何悦', '何小悦'), ('高明', '高小明'), ('郑宇', '郑小宇'),
    ('谢薇', '谢小薇'), ('宋博', '宋小博'), ('唐涛', '唐小涛'), ('许洁', '许小洁'),
    ('韩梅', '韩小梅'), ('冯亮', '冯小亮'), ('董凯', '董小凯'), ('潘雪', '潘小雪'),
    ('袁浩', '袁小浩'), ('蒋雯', '蒋小雯')
]

def get_db():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def generate_phone():
    prefix = random.choice(['138', '139', '136', '137', '135', '150', '151', '152', '157', '158', '159', '182', '183', '187', '188'])
    suffix = ''.join(random.choices('0123456789', k=8))
    return prefix + suffix

def generate_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(10))

def insert_courses(conn):
    cursor = conn.cursor()
    course_ids = []
    for course in courses_data:
        cursor.execute('''
            INSERT INTO courses (name, description, total_hours, price, start_time, end_time, max_students, current_students)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (course['name'], course['description'], course['total_hours'], course['price'], course['start_time'], course['end_time'], course['max_students']))
        course_ids.append(cursor.lastrowid)
    conn.commit()
    print(f'已插入 {len(course_ids)} 个课程')
    return course_ids

def insert_students(conn, count=30):
    cursor = conn.cursor()
    # 先获取已有的普通用户
    cursor.execute("SELECT id FROM users WHERE role = 'user'")
    existing = [row['id'] for row in cursor.fetchall()]
    
    user_ids = existing.copy()
    needed = count - len(existing)
    
    random.shuffle(student_names)
    for i in range(needed):
        parent_name, child_name = student_names[i % len(student_names)]
        # 避免名字重复，加序号
        if i >= len(student_names):
            parent_name = parent_name + str(i // len(student_names) + 1)
            child_name = child_name + str(i // len(student_names) + 1)
        
        username = 'user_' + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))
        password = generate_password()
        phone = generate_phone()
        
        cursor.execute('''
            INSERT INTO users (username, password, name, phone, child_name, role)
            VALUES (?, ?, ?, ?, ?, 'user')
        ''', (username, hash_password(password), parent_name, phone, child_name))
        user_ids.append(cursor.lastrowid)
    
    conn.commit()
    print(f'已有 {len(existing)} 个用户，新增 {needed} 个，共 {len(user_ids)} 个学员')
    return user_ids

def enroll_students(conn, user_ids, course_ids):
    cursor = conn.cursor()
    enrollment_records = []
    
    # 每个学员随机报名 1-3 个课程
    for user_id in user_ids:
        num_courses = random.randint(1, 3)
        selected = random.sample(course_ids, min(num_courses, len(course_ids)))
        
        for course_id in selected:
            # 检查课程是否已满
            course = cursor.execute('SELECT * FROM courses WHERE id = ?', (course_id,)).fetchone()
            if course['current_students'] >= course['max_students']:
                continue
            
            # 检查是否已报名
            existing = cursor.execute('SELECT * FROM enrollments WHERE user_id = ? AND course_id = ?', (user_id, course_id)).fetchone()
            if existing:
                continue
            
            cursor.execute('BEGIN TRANSACTION')
            try:
                cursor.execute('''
                    INSERT INTO enrollments (user_id, course_id, status, payment_amount, payment_time, attendance_count)
                    VALUES (?, ?, 'paid', ?, datetime('now'), 0)
                ''', (user_id, course_id, course['price']))
                enrollment_id = cursor.lastrowid
                
                cursor.execute('UPDATE courses SET current_students = current_students + 1 WHERE id = ?', (course_id,))
                cursor.execute('COMMIT')
                
                enrollment_records.append({
                    'enrollment_id': enrollment_id,
                    'course_id': course_id,
                    'user_id': user_id,
                    'total_hours': course['total_hours']
                })
            except Exception as e:
                cursor.execute('ROLLBACK')
                print(f'报名失败 user={user_id} course={course_id}: {e}')
    
    conn.commit()
    print(f'已创建 {len(enrollment_records)} 条报名记录')
    return enrollment_records

def generate_attendance(conn, enrollment_records):
    cursor = conn.cursor()
    attendance_count = 0
    
    for rec in enrollment_records:
        # 每个报名记录随机签到 0 到课程总课时数-4 次（留一些未上的课）
        max_attendance = max(0, rec['total_hours'] // 2 - 4)
        num_classes = random.randint(0, max_attendance)
        
        # 生成连续的上课日期
        base_date = random.choice(['2026-03-05', '2026-03-08', '2026-03-10', '2026-03-12'])
        from datetime import datetime, timedelta
        start = datetime.strptime(base_date, '%Y-%m-%d')
        
        for i in range(num_classes):
            class_date = (start + timedelta(days=i * 7)).strftime('%Y-%m-%d')
            status = random.choices(['present', 'present', 'present', 'absent'], weights=[70, 15, 10, 5])[0]
            
            cursor.execute('''
                INSERT INTO attendances (enrollment_id, class_date, class_number, status)
                VALUES (?, ?, ?, ?)
            ''', (rec['enrollment_id'], class_date, i + 1, status))
            attendance_count += 1
        
        # 更新报名记录的签到次数（只统计 present）
        cursor.execute('''
            UPDATE enrollments SET attendance_count = (
                SELECT COUNT(*) FROM attendances WHERE enrollment_id = ? AND status = 'present'
            ) WHERE id = ?
        ''', (rec['enrollment_id'], rec['enrollment_id']))
    
    conn.commit()
    print(f'已生成 {attendance_count} 条签到记录')

def main():
    conn = get_db()
    try:
        print('开始生成测试数据...')
        print('-' * 40)
        
        course_ids = insert_courses(conn)
        user_ids = insert_students(conn, 30)
        enrollment_records = enroll_students(conn, user_ids, course_ids)
        generate_attendance(conn, enrollment_records)
        
        print('-' * 40)
        print('测试数据生成完成！')
        
        # 统计
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM courses')
        print(f'课程总数: {cursor.fetchone()[0]}')
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'user'")
        print(f'学员总数: {cursor.fetchone()[0]}')
        cursor.execute('SELECT COUNT(*) FROM enrollments')
        print(f'报名总数: {cursor.fetchone()[0]}')
        cursor.execute('SELECT COUNT(*) FROM attendances')
        print(f'签到总数: {cursor.fetchone()[0]}')
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()
