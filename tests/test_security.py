#!/usr/bin/env python3
"""
测试模块：安全性测试
覆盖：SQL注入、XSS、权限越界、CSRF防护、Session安全、频率限制、密码安全
"""

import json
import pytest


class TestSQLInjection:
    """SQL注入防护测试"""

    def test_login_sql_injection_union(self, client):
        """TC-SQL-01: 登录时尝试 UNION 注入应失败"""
        import time
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': "' OR '1'='1",
            'password': 'anything',
            'captcha': '1234'
        })
        assert resp.status_code == 200
        # 返回登录页面HTML，提示用户名或密码错误
        assert b'\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81' in resp.data

    def test_login_sql_injection_comment(self, client):
        """TC-SQL-02: 登录时尝试注释注入应失败"""
        import time
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': "admin'--",
            'password': 'anything',
            'captcha': '1234'
        })
        assert resp.status_code == 200
        assert b'\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81' in resp.data

    def test_login_sql_injection_union_select(self, client):
        """TC-SQL-03: 登录时尝试 UNION SELECT 注入应失败"""
        import time
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': "' UNION SELECT * FROM users --",
            'password': 'anything',
            'captcha': '1234'
        })
        assert resp.status_code == 200
        assert b'\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81' in resp.data

    def test_send_message_sql_injection(self, user_logged_in):
        """TC-SQL-04: 消息内容中包含 SQL 注入语句应作为纯文本处理"""
        admin_id = user_logged_in.test_data['admin_id']
        resp = user_logged_in.post('/send_message', data={
            'receiver_id': admin_id,
            'content': "'; DROP TABLE users; --"
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_enroll_sql_injection_in_json(self, user_logged_in):
        """TC-SQL-05: 报名JSON中包含 SQL 注入应被参数化查询安全处理"""
        course1_id = user_logged_in.test_data['course1_id']
        resp = user_logged_in.post(f'/enroll/{course1_id}',
            data=json.dumps({'alternate_courses': ["1; DROP TABLE courses;"]}),
            content_type='application/json')
        assert resp.status_code == 200
        # 后续请求应仍能正常执行，说明表未被删除
        resp2 = user_logged_in.get('/courses')
        assert resp2.status_code == 200


class TestXSS:
    """XSS跨站脚本攻击防护测试"""

    def test_send_message_xss_script(self, user_logged_in):
        """TC-XSS-01: 消息中发送 <script> 标签应作为纯文本存储"""
        admin_id = user_logged_in.test_data['admin_id']
        xss_payload = '<script>alert("XSS")</script>'
        resp = user_logged_in.post('/send_message', data={
            'receiver_id': admin_id,
            'content': xss_payload
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        # 获取聊天记录验证内容未被过滤但未被当作脚本执行
        resp2 = user_logged_in.get(f'/api/conversation/{admin_id}')
        assert resp2.status_code == 200
        data2 = json.loads(resp2.data)
        assert data2['success'] is True
        if data2['messages']:
            # 内容应完整保留（后端不做HTML转义，由前端负责）
            assert xss_payload in str(data2['messages'])

    def test_send_message_xss_img_onerror(self, user_logged_in):
        """TC-XSS-02: 消息中发送 onerror 事件应作为纯文本处理"""
        admin_id = user_logged_in.test_data['admin_id']
        xss_payload = '<img src=x onerror=alert(1)>'
        resp = user_logged_in.post('/send_message', data={
            'receiver_id': admin_id,
            'content': xss_payload
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_send_message_xss_javascript_protocol(self, user_logged_in):
        """TC-XSS-03: javascript: 伪协议应作为纯文本处理"""
        admin_id = user_logged_in.test_data['admin_id']
        xss_payload = '<a href="javascript:alert(1)">点击</a>'
        resp = user_logged_in.post('/send_message', data={
            'receiver_id': admin_id,
            'content': xss_payload
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True


class TestPrivilegeEscalation:
    """权限越界测试"""

    def test_user_access_admin_api_add_course(self, user_logged_in):
        """TC-PRIV-01: 普通用户 POST /admin/add_course 应被重定向"""
        resp = user_logged_in.post('/admin/add_course', data={
            'name': '黑客课程',
            'total_hours': 1,
            'price': 0,
            'start_time': '2026-01-01',
            'end_time': '2026-02-01',
            'max_students': 1
        }, follow_redirects=False)
        assert resp.status_code == 302

    def test_user_access_admin_api_delete_course(self, user_logged_in):
        """TC-PRIV-02: 普通用户删除课程应被重定向"""
        resp = user_logged_in.post('/admin/delete_course/1', follow_redirects=False)
        assert resp.status_code == 302

    def test_user_access_admin_api_attendance(self, user_logged_in):
        """TC-PRIV-03: 普通用户访问签到页应被重定向"""
        resp = user_logged_in.get('/admin/attendance/1', follow_redirects=False)
        assert resp.status_code == 302

    def test_user_access_hours_management(self, user_logged_in):
        """TC-PRIV-04: 普通用户访问课时管理应被重定向"""
        resp = user_logged_in.get('/admin/hours_management', follow_redirects=False)
        assert resp.status_code == 302

    def test_user_move_student_api(self, user_logged_in):
        """TC-PRIV-05: 普通用户调用 move_student 应返回权限不足"""
        resp = user_logged_in.post('/move_student',
            data=json.dumps({
                'student_id': 1,
                'current_course_id': 1,
                'target_course_id': 3
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_user_remove_student_api(self, user_logged_in):
        """TC-PRIV-06: 普通用户调用 remove_student 应返回权限不足"""
        resp = user_logged_in.post('/remove_student',
            data=json.dumps({'enrollment_id': 1}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_user_temp_adjust_api(self, user_logged_in):
        """TC-PRIV-07: 普通用户调用 temp_adjust 应返回权限不足"""
        resp = user_logged_in.post('/temp_adjust',
            data=json.dumps({
                'enrollment_id': 1,
                'course_id': 1,
                'class_date': '2026-04-01'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_user_add_student_api(self, user_logged_in):
        """TC-PRIV-08: 普通用户调用 add_student 应返回权限不足"""
        resp = user_logged_in.post('/add_student',
            data=json.dumps({
                'course_id': 1,
                'child_name': '测试',
                'parent_name': '家长',
                'phone': '13800138000'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_user_access_api_contacts(self, user_logged_in):
        """TC-PRIV-09: 普通用户获取联系人列表应返回403"""
        resp = user_logged_in.get('/api/contacts')
        assert resp.status_code == 403

    def test_user_access_other_user_conversation(self, user_logged_in):
        """TC-PRIV-10: 普通用户查看与其他用户的对话应返回403"""
        user2_id = user_logged_in.test_data['user2_id']
        resp = user_logged_in.get(f'/api/conversation/{user2_id}')
        assert resp.status_code == 403


class TestSessionSecurity:
    """Session安全测试"""

    def test_session_http_only(self, client):
        """TC-SESS-01: Session Cookie 应设置 HttpOnly"""
        # 先登录
        import time
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'captcha': '1234'
        })
        # 注意：测试客户端不实际设置 cookie，这里验证配置
        from app import app
        assert app.config.get('SESSION_COOKIE_HTTPONLY') is True

    def test_session_samesite(self):
        """TC-SESS-02: Session Cookie 应设置 SameSite"""
        from app import app
        assert app.config.get('SESSION_COOKIE_SAMESITE') == 'Lax'

    def test_session_has_lifetime(self):
        """TC-SESS-03: Session 应有过期时间配置"""
        from app import app
        from datetime import timedelta
        lifetime = app.config.get('PERMANENT_SESSION_LIFETIME')
        assert lifetime is not None
        assert isinstance(lifetime, timedelta)


class TestRateLimit:
    """频率限制测试"""

    def test_rate_limit_triggers_after_5_requests(self, client):
        """TC-RATE-01: 同一IP连续6次请求应触发429"""
        import app.routes.main as main_module
        main_module.request_limits.clear()
        import time
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        # 5次正常请求
        for i in range(5):
            resp = client.post('/login', data={
                'username': 'admin',
                'password': f'wrong{i}',
                'captcha': '1234'
            })
            assert resp.status_code == 200
        # 第6次应429
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'wrong5',
            'captcha': '1234'
        })
        assert resp.status_code == 429

    def test_rate_limit_429_response_format(self, client):
        """TC-RATE-02: 429响应应包含友好提示"""
        import app.routes.main as main_module
        main_module.request_limits.clear()
        import time
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        for i in range(5):
            client.post('/login', data={
                'username': 'admin',
                'password': f'wrong{i}',
                'captcha': '1234'
            })
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'wrong5',
            'captcha': '1234'
        })
        assert resp.status_code == 429
        data = json.loads(resp.data)
        assert data['success'] is False
        assert 'message' in data


class TestErrorHandlers:
    """全局错误处理测试"""

    def test_404_api_returns_json(self, client):
        """TC-ERR-01: API 404请求应返回JSON"""
        resp = client.get('/api/nonexistent', headers={'Accept': 'application/json'})
        # 实际上 Flask request.is_json 是检查 content-type
        resp = client.get('/api/nonexistent', content_type='application/json')
        assert resp.status_code == 404
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_404_page_returns_template(self, client):
        """TC-ERR-02: 页面 404请求应渲染模板"""
        resp = client.get('/nonexistent-page')
        assert resp.status_code == 404

    def test_500_error_handler_exists(self):
        """TC-ERR-03: 500错误处理器应已注册"""
        from app import app
        assert 500 in app.error_handler_spec[None]

    def test_429_error_handler_exists(self):
        """TC-ERR-04: 429错误处理器应已注册"""
        from app import app
        assert 429 in app.error_handler_spec[None]
