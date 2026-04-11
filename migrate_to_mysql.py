#!/usr/bin/env python3
"""
SQLite 到 MySQL 数据迁移脚本
使用方法：
1. 确保 MySQL 已启动（phpStudy）
2. 在 MySQL 中执行 mysql_schema.sql 创建表结构
3. 运行：python migrate_to_mysql.py
"""

import sqlite3
import os
import sys

try:
    import pymysql
except ImportError:
    print("错误：请先安装 PyMySQL：pip install pymysql")
    sys.exit(1)

# ============ 配置 ============
SQLITE_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calligraphy_system.db')

MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',           # phpStudy 默认 root
    'password': 'root',       # phpStudy 默认密码，请根据实际情况修改
    'database': 'calligraphy_system',
    'charset': 'utf8mb4'
}
# ==============================

TABLES = ['users', 'courses', 'enrollments', 'attendances', 'alternate_courses', 'messages']


def get_sqlite_conn():
    """获取 SQLite 连接"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_mysql_conn():
    """获取 MySQL 连接"""
    return pymysql.connect(
        host=MYSQL_CONFIG['host'],
        port=MYSQL_CONFIG['port'],
        user=MYSQL_CONFIG['user'],
        password=MYSQL_CONFIG['password'],
        database=MYSQL_CONFIG['database'],
        charset=MYSQL_CONFIG['charset'],
        cursorclass=pymysql.cursors.DictCursor
    )


def migrate_table(sqlite_cur, mysql_cur, table_name):
    """迁移单张表的数据"""
    sqlite_cur.execute(f'SELECT * FROM {table_name}')
    rows = sqlite_cur.fetchall()
    
    if not rows:
        print(f'  [{table_name}] 无数据，跳过')
        return 0
    
    columns = list(rows[0].keys())
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(columns)
    
    insert_sql = f'INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})'
    
    count = 0
    for row in rows:
        values = [row[col] for col in columns]
        try:
            mysql_cur.execute(insert_sql, values)
            count += 1
        except Exception as e:
            print(f'  [{table_name}] 插入失败 id={row.get("id", "?")}: {e}')
    
    print(f'  [{table_name}] 成功迁移 {count}/{len(rows)} 条记录')
    return count


def reset_mysql_auto_increment(mysql_cur, table_name):
    """重置 MySQL 自增 ID 起点"""
    mysql_cur.execute(f'SELECT MAX(id) as max_id FROM {table_name}')
    result = mysql_cur.fetchone()
    max_id = result['max_id'] or 0
    if max_id > 0:
        mysql_cur.execute(f'ALTER TABLE {table_name} AUTO_INCREMENT = {max_id + 1}')
        print(f'  [{table_name}] 自增ID重置为 {max_id + 1}')


def main():
    print('=' * 50)
    print('SQLite -> MySQL 数据迁移工具')
    print('=' * 50)
    
    if not os.path.exists(SQLITE_DB_PATH):
        print(f'错误：找不到 SQLite 数据库文件：{SQLITE_DB_PATH}')
        sys.exit(1)
    
    print(f'\n源数据库：{SQLITE_DB_PATH}')
    print(f'目标数据库：MySQL {MYSQL_CONFIG["host"]}:{MYSQL_CONFIG["port"]}/{MYSQL_CONFIG["database"]}')
    print(f'目标表：{TABLES}')
    
    confirm = input('\n确认开始迁移吗？数据将覆盖目标表现有数据 [y/N]: ')
    if confirm.lower() != 'y':
        print('已取消迁移')
        return
    
    sqlite_conn = get_sqlite_conn()
    sqlite_cur = sqlite_conn.cursor()
    
    mysql_conn = get_mysql_conn()
    mysql_cur = mysql_conn.cursor()
    
    total = 0
    try:
        for table in TABLES:
            print(f'\n正在迁移表：{table} ...')
            # 清空目标表（保留表结构）
            mysql_cur.execute(f'DELETE FROM {table}')
            count = migrate_table(sqlite_cur, mysql_cur, table)
            if count > 0:
                reset_mysql_auto_increment(mysql_cur, table)
            total += count
        
        mysql_conn.commit()
        print(f'\n{"=" * 50}')
        print(f'迁移完成！共迁移 {total} 条记录')
        print(f'{"=" * 50}')
        
    except Exception as e:
        mysql_conn.rollback()
        print(f'\n迁移失败，已回滚：{e}')
    finally:
        sqlite_conn.close()
        mysql_conn.close()


if __name__ == '__main__':
    main()
