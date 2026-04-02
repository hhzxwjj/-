-- MySQL 数据库建表语句（书法报名管理系统）
-- 字符集：utf8mb4，支持中文和Emoji

CREATE DATABASE IF NOT EXISTS calligraphy_system
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_unicode_ci;

USE calligraphy_system;

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键，用户唯一标识',
    username VARCHAR(64) UNIQUE NOT NULL COMMENT '用户名，唯一',
    password VARCHAR(255) NOT NULL COMMENT '密码哈希值（PBKDF2）',
    name VARCHAR(50) DEFAULT NULL COMMENT '家长姓名',
    phone VARCHAR(20) DEFAULT NULL COMMENT '手机号',
    email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
    child_name VARCHAR(50) DEFAULT NULL COMMENT '孩子姓名',
    role VARCHAR(20) DEFAULT 'user' COMMENT '角色：admin/user',
    INDEX idx_phone (phone),
    INDEX idx_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表（家长/管理员）';

-- 课程表
CREATE TABLE IF NOT EXISTS courses (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    name VARCHAR(100) NOT NULL COMMENT '课程名称',
    description TEXT COMMENT '课程描述',
    total_hours INT DEFAULT NULL COMMENT '总课时数',
    price DECIMAL(10,2) DEFAULT NULL COMMENT '课程价格（元）',
    start_time DATE DEFAULT NULL COMMENT '开始日期',
    end_time DATE DEFAULT NULL COMMENT '结束日期',
    max_students INT DEFAULT NULL COMMENT '最大学员数',
    current_students INT DEFAULT 0 COMMENT '当前学员数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='课程表';

-- 报名记录表
CREATE TABLE IF NOT EXISTS enrollments (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    user_id INT DEFAULT NULL COMMENT '外键-用户ID',
    course_id INT DEFAULT NULL COMMENT '外键-课程ID',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态：pending/paid',
    payment_amount DECIMAL(10,2) DEFAULT NULL COMMENT '缴费金额',
    payment_time DATETIME DEFAULT NULL COMMENT '缴费时间',
    attendance_count INT DEFAULT 0 COMMENT '已出勤次数',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_course_id (course_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='报名记录表';

-- 签到记录表
CREATE TABLE IF NOT EXISTS attendances (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    enrollment_id INT DEFAULT NULL COMMENT '外键-报名记录ID',
    class_date DATE DEFAULT NULL COMMENT '上课日期',
    class_number INT DEFAULT NULL COMMENT '课次序号',
    status VARCHAR(20) DEFAULT 'absent' COMMENT '状态：present/absent/leave',
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_enrollment_id (enrollment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='签到记录表';

-- 备选课程表
CREATE TABLE IF NOT EXISTS alternate_courses (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    enrollment_id INT DEFAULT NULL COMMENT '外键-报名记录ID',
    course_id INT DEFAULT NULL COMMENT '外键-课程ID',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态',
    FOREIGN KEY (enrollment_id) REFERENCES enrollments(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='备选课程表';

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
    sender_id INT DEFAULT NULL COMMENT '外键-发送者ID',
    receiver_id INT DEFAULT NULL COMMENT '外键-接收者ID',
    content TEXT COMMENT '消息内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    status VARCHAR(20) DEFAULT 'unread' COMMENT '状态：unread/read',
    FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    INDEX idx_sender_id (sender_id),
    INDEX idx_receiver_id (receiver_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';
