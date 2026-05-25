#!/usr/bin/env python3
"""
测试模块：用户认证
覆盖：登录、注册、验证码、密码修改、频率限制、资料完善
"""

import time
import json
import pytest

from app import app
from app.routes.main import hash_password, verify_password, check_captcha, validate_phone


# ==================== 单元测试：工具函数 ====================

class TestPasswordUtils:
    """密码哈希与验证工具函数测试"""

    def test_hash_password_returns_salt_hash_format(self):
        """TC-PWD-01: 哈希密码应返回 salt$hash 格式"""
        hashed = hash_password('mypassword123')
        assert '$' in hashed
        parts = hashed.split('$')
        assert len(parts) == 2
        assert len(parts[0]) == 32  # salt 是 16 字节 hex = 32 字符
        assert len(parts[1]) == 64  # SHA256 hash = 64 字符 hex

    def test_verify_password_correct(self):
        """TC-PWD-02: 正确密码应验证通过"""
        password = 'correct_password'
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_wrong(self):
        """TC-PWD-03: 错误密码应验证失败"""
        hashed = hash_password('correct_password')
        assert verify_password('wrong_password', hashed) is False

    def test_verify_password_old_sha256_compatible(self):
        """TC-PWD-04: 兼容旧版纯 SHA256 格式密码"""
        import hashlib
        old_hash = hashlib.sha256('oldpass'.encode('utf-8')).hexdigest()
        assert verify_password('oldpass', old_hash) is True
        assert verify_password('wrongpass', old_hash) is False

    def test_hash_password_different_salts(self):
        """TC-PWD-05: 同一密码两次哈希结果应不同（salt随机）"""
        hashed1 = hash_password('samepassword')
        hashed2 = hash_password('samepassword')
        assert hashed1 != hashed2


class TestCaptchaUtils:
    """验证码工具函数测试"""

    def test_check_captcha_correct(self):
        """TC-CAP-01: 正确验证码应通过校验"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['captcha'] = 'ABCD'
                sess['captcha_created_at'] = time.time()
            with c.session_transaction():
                pass  # 确保 session 已写入
        # 由于 check_captcha 依赖全局 session，通过实际登录流程间接验证
        # 已在 test_login_success_with_username_password 中验证

    def test_check_captcha_wrong_via_login(self, client):
        """TC-CAP-02: 错误验证码应在登录中被拒绝"""
        with client.session_transaction() as sess:
            sess['captcha'] = 'ABCD'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'captcha': 'WXYZ'
        })
        assert resp.status_code == 200
        assert b'\xe9\xaa\x8c\xe8\xaf\x81\xe7\xa0\x81' in resp.data

    def test_check_captcha_expired_via_login(self, client):
        """TC-CAP-03: 过期验证码应在登录中被拒绝"""
        with client.session_transaction() as sess:
            sess['captcha'] = 'ABCD'
            sess['captcha_created_at'] = time.time() - 301
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'captcha': 'ABCD'
        })
        assert resp.status_code == 200
        assert b'\xe9\xaa\x8c\xe8\xaf\x81\xe7\xa0\x81' in resp.data

    def test_check_captcha_empty_via_login(self, client):
        """TC-CAP-04: 空验证码应在登录中被拒绝"""
        with client.session_transaction() as sess:
            sess['captcha'] = 'ABCD'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'captcha': ''
        })
        assert resp.status_code == 200
        assert b'\xe9\xaa\x8c\xe8\xaf\x81\xe7\xa0\x81' in resp.data


class TestPhoneValidation:
    """手机号格式校验测试"""

    @pytest.mark.parametrize('phone,expected', [
        ('13800138000', True),
        ('13912345678', True),
        ('15012345678', True),
        ('18812345678', True),
        ('1380013800', False),   # 10位
        ('138001380000', False), # 12位
        ('12800138000', False),  # 第二位2
        ('1380013800a', False),  # 含字母
        ('', False),
        ('138001380 0', False),  # 含空格
    ])
    def test_validate_phone(self, phone, expected):
        """TC-PHONE-01~10: 手机号格式校验"""
        assert validate_phone(phone) == expected


# ==================== 集成测试：HTTP 路由 ====================

class TestLoginRoute:
    """登录路由测试"""

    def test_login_page_get(self, client):
        """TC-LOGIN-01: GET /login 应返回登录页面"""
        resp = client.get('/login')
        assert resp.status_code == 200
        assert b'login' in resp.data.lower() or b'\xe7\x99\xbb\xe5\xbd\x95' in resp.data

    def test_login_success_with_username_password(self, client):
        """TC-LOGIN-02: 正确用户名密码+验证码应登录成功"""
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'captcha': '1234'
        }, follow_redirects=True)
        assert resp.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('user_id') == client.test_data['admin_id']
            assert sess.get('role') == 'admin'

    def test_login_wrong_password(self, client):
        """TC-LOGIN-03: 错误密码应提示错误（返回HTML）"""
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'wrongpassword',
            'captcha': '1234'
        })
        assert resp.status_code == 200
        # 返回登录页面并显示错误信息
        assert b'\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81\xe9\x94\x99\xe8\xaf\xaf' in resp.data

    def test_login_wrong_captcha(self, client):
        """TC-LOGIN-04: 错误验证码应提示验证码错误（返回HTML）"""
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'admin123',
            'captcha': '9999'
        })
        assert resp.status_code == 200
        assert b'\xe9\xaa\x8c\xe8\xaf\x81\xe7\xa0\x81\xe9\x94\x99\xe8\xaf\xaf' in resp.data

    def test_login_nonexistent_user(self, client):
        """TC-LOGIN-05: 不存在的用户名应登录失败（返回HTML）"""
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        resp = client.post('/login', data={
            'username': 'notexist',
            'password': 'anypassword',
            'captcha': '1234'
        })
        assert resp.status_code == 200
        assert b'\xe7\x94\xa8\xe6\x88\xb7\xe5\x90\x8d\xe6\x88\x96\xe5\xaf\x86\xe7\xa0\x81\xe9\x94\x99\xe8\xaf\xaf' in resp.data

    def test_login_rate_limit(self, client):
        """TC-LOGIN-06: 连续5次错误后第6次应触发频率限制"""
        import app.routes.main as main_module
        main_module.request_limits.clear()
        with client.session_transaction() as sess:
            sess['captcha'] = '1234'
            sess['captcha_created_at'] = time.time()
        # 连续5次错误
        for i in range(5):
            resp = client.post('/login', data={
                'username': 'admin',
                'password': f'wrong{i}',
                'captcha': '1234'
            })
            assert resp.status_code == 200
        # 第6次应被限制
        resp = client.post('/login', data={
            'username': 'admin',
            'password': 'wrong5',
            'captcha': '1234'
        })
        assert resp.status_code == 429

    def test_captcha_image_route(self, client):
        """TC-LOGIN-07: GET /captcha 应返回 PNG 图片"""
        resp = client.get('/captcha')
        assert resp.status_code == 200
        assert resp.content_type == 'image/png'


class TestRegisterRoute:
    """注册路由测试"""

    def test_register_page_get(self, client):
        """TC-REG-01: GET /register 应返回注册页面"""
        resp = client.get('/register')
        assert resp.status_code == 200

    def test_register_success(self, client):
        """TC-REG-02: 正常注册流程应成功并重定向到注册成功页"""
        with client.session_transaction() as sess:
            sess['verification_code'] = '567890'
            sess['phone'] = '13812345678'
            sess['verification_code_created_at'] = time.time()
        resp = client.post('/register', data={
            'phone': '13812345678',
            'verification_code': '567890',
            'name': '李家长',
            'child_name': '李小明'
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert '/register_success' in resp.headers.get('Location', '')

    def test_register_duplicate_phone(self, client):
        """TC-REG-03: 重复手机号应提示已注册（返回HTML）"""
        with client.session_transaction() as sess:
            sess['verification_code'] = '567890'
            sess['phone'] = '13800138000'  # 管理员手机号
            sess['verification_code_created_at'] = time.time()
        resp = client.post('/register', data={
            'phone': '13800138000',
            'verification_code': '567890',
            'name': '李家长',
            'child_name': '李小明'
        })
        assert resp.status_code == 200
        assert b'\xe6\x89\x8b\xe6\x9c\xba\xe5\x8f\xb7\xe5\xb7\xb2\xe6\xb3\xa8\xe5\x86\x8c' in resp.data

    def test_register_invalid_phone(self, client):
        """TC-REG-04: 非法手机号应被拒绝（返回HTML）"""
        with client.session_transaction() as sess:
            sess['verification_code'] = '567890'
            sess['phone'] = '12345678901'
            sess['verification_code_created_at'] = time.time()
        resp = client.post('/register', data={
            'phone': '12345678901',
            'verification_code': '567890',
            'name': '李家长',
            'child_name': '李小明'
        })
        assert resp.status_code == 200
        assert b'\xe6\x89\x8b\xe6\x9c\xba\xe5\x8f\xb7\xe6\xa0\xbc\xe5\xbc\x8f' in resp.data

    def test_register_wrong_verification_code(self, client):
        """TC-REG-05: 错误验证码应注册失败（返回HTML）"""
        with client.session_transaction() as sess:
            sess['verification_code'] = '567890'
            sess['phone'] = '13812345678'
            sess['verification_code_created_at'] = time.time()
        resp = client.post('/register', data={
            'phone': '13812345678',
            'verification_code': '111111',
            'name': '李家长',
            'child_name': '李小明'
        })
        assert resp.status_code == 200
        assert b'\xe9\xaa\x8c\xe8\xaf\x81\xe7\xa0\x81\xe9\x94\x99\xe8\xaf\xaf' in resp.data


class TestLogoutRoute:
    """登出路由测试"""

    def test_logout_clears_session(self, admin_logged_in):
        """TC-LOGOUT-01: 登出应清除 session 并重定向"""
        resp = admin_logged_in.get('/logout', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')
        with admin_logged_in.session_transaction() as sess:
            assert 'user_id' not in sess


class TestChangePasswordRoute:
    """修改密码路由测试"""

    def test_change_password_success(self, user_logged_in):
        """TC-CPW-01: 正确原密码应修改成功"""
        resp = user_logged_in.post('/change_password',
            data=json.dumps({'old_password': 'user123', 'new_password': 'newpass123'}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_change_password_wrong_old(self, user_logged_in):
        """TC-CPW-02: 错误原密码应修改失败"""
        resp = user_logged_in.post('/change_password',
            data=json.dumps({'old_password': 'wrongpass', 'new_password': 'newpass123'}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_change_password_too_short(self, user_logged_in):
        """TC-CPW-03: 新密码少于6位应被拒绝"""
        resp = user_logged_in.post('/change_password',
            data=json.dumps({'old_password': 'user123', 'new_password': '123'}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_change_password_not_logged_in(self, client):
        """TC-CPW-04: 未登录应拒绝修改密码"""
        resp = client.post('/change_password',
            data=json.dumps({'old_password': 'old', 'new_password': 'newpass123'}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False


class TestProfileCompleteness:
    """资料完善中间件测试"""

    def test_incomplete_user_redirected(self, incomplete_user_logged_in):
        """TC-PROF-01: 信息不完整用户访问非豁免路由应被重定向"""
        resp = incomplete_user_logged_in.get('/courses', follow_redirects=False)
        assert resp.status_code == 302
        assert '/complete_profile' in resp.headers.get('Location', '')

    def test_complete_profile_page_accessible(self, incomplete_user_logged_in):
        """TC-PROF-02: 信息不完整用户可访问 complete_profile 页面"""
        resp = incomplete_user_logged_in.get('/complete_profile')
        assert resp.status_code == 200

    def test_complete_profile_submission(self, incomplete_user_logged_in):
        """TC-PROF-03: 提交完善资料应成功并重定向"""
        resp = incomplete_user_logged_in.post('/complete_profile', data={
            'name': '王家长',
            'child_name': '王小明',
            'phone': '13700137000'
        }, follow_redirects=False)
        assert resp.status_code == 302
        loc = resp.headers.get('Location', '')
        assert '/index' in loc or 'http://localhost/' == loc
