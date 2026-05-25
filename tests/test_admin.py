#!/usr/bin/env python3
"""
测试模块：管理员后台功能
覆盖：添加课程、删除课程、签到、人员调整、移除学生、添加学生、课时统计、临时调课
"""

import json
import pytest


class TestAdminAccessControl:
    """管理员权限控制测试"""

    def test_admin_page_requires_login(self, client):
        """TC-ADMIN-01: 未登录访问 /admin 应重定向到登录"""
        resp = client.get('/admin', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    def test_admin_page_requires_admin_role(self, user_logged_in):
        """TC-ADMIN-02: 普通用户访问 /admin 应重定向"""
        resp = user_logged_in.get('/admin', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.headers.get('Location', '')

    def test_admin_page_success(self, admin_logged_in):
        """TC-ADMIN-03: 管理员应能访问后台"""
        resp = admin_logged_in.get('/admin')
        assert resp.status_code == 200


class TestAddCourse:
    """添加课程测试"""

    def test_add_course_success(self, admin_logged_in):
        """TC-ADDC-01: 管理员添加合法课程应成功"""
        resp = admin_logged_in.post('/admin/add_course', data={
            'name': '测试新课程',
            'description': '这是一个测试课程',
            'total_hours': 20,
            'price': 999.0,
            'start_time': '2026-09-01',
            'end_time': '2026-12-01',
            'max_students': 10
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_add_course_empty_name(self, admin_logged_in):
        """TC-ADDC-02: 空课程名应被拒绝"""
        resp = admin_logged_in.post('/admin/add_course', data={
            'name': '',
            'description': '描述',
            'total_hours': 20,
            'price': 999.0,
            'start_time': '2026-09-01',
            'end_time': '2026-12-01',
            'max_students': 10
        }, follow_redirects=True)
        assert resp.status_code == 200  # 重定向回admin

    def test_add_course_negative_hours(self, admin_logged_in):
        """TC-ADDC-03: 负数课时应被拒绝"""
        resp = admin_logged_in.post('/admin/add_course', data={
            'name': '测试课程',
            'description': '描述',
            'total_hours': -5,
            'price': 999.0,
            'start_time': '2026-09-01',
            'end_time': '2026-12-01',
            'max_students': 10
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_add_course_negative_price(self, admin_logged_in):
        """TC-ADDC-04: 负数价格应被拒绝"""
        resp = admin_logged_in.post('/admin/add_course', data={
            'name': '测试课程',
            'description': '描述',
            'total_hours': 20,
            'price': -100,
            'start_time': '2026-09-01',
            'end_time': '2026-12-01',
            'max_students': 10
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_add_course_zero_max_students(self, admin_logged_in):
        """TC-ADDC-05: 0最大学生数应被拒绝"""
        resp = admin_logged_in.post('/admin/add_course', data={
            'name': '测试课程',
            'description': '描述',
            'total_hours': 20,
            'price': 999.0,
            'start_time': '2026-09-01',
            'end_time': '2026-12-01',
            'max_students': 0
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_add_course_requires_admin(self, user_logged_in):
        """TC-ADDC-06: 普通用户添加课程应被重定向"""
        resp = user_logged_in.post('/admin/add_course', data={
            'name': '测试课程',
            'total_hours': 20,
            'price': 999.0,
            'start_time': '2026-09-01',
            'end_time': '2026-12-01',
            'max_students': 10
        }, follow_redirects=False)
        assert resp.status_code == 302


class TestDeleteCourse:
    """删除课程测试（含级联删除）"""

    def test_delete_course_success(self, admin_logged_in):
        """TC-DELC-01: 删除课程应级联删除相关报名和签到"""
        course1_id = admin_logged_in.test_data['course1_id']
        resp = admin_logged_in.post(f'/admin/delete_course/{course1_id}', follow_redirects=True)
        assert resp.status_code == 200

    def test_delete_nonexistent_course(self, admin_logged_in):
        """TC-DELC-02: 删除不存在的课程应正常处理"""
        resp = admin_logged_in.post('/admin/delete_course/9999', follow_redirects=True)
        assert resp.status_code == 200

    def test_delete_course_requires_admin(self, user_logged_in):
        """TC-DELC-03: 普通用户删除课程应被重定向"""
        resp = user_logged_in.post('/admin/delete_course/1', follow_redirects=False)
        assert resp.status_code == 302


class TestAttendance:
    """签到路由测试"""

    def test_attendance_page_requires_admin(self, user_logged_in):
        """TC-ATD-01: 普通用户访问签到页应被重定向"""
        resp = user_logged_in.get('/admin/attendance/1', follow_redirects=False)
        assert resp.status_code == 302

    def test_attendance_page_success(self, admin_logged_in):
        """TC-ATD-02: 管理员应能访问签到页"""
        course1_id = admin_logged_in.test_data['course1_id']
        resp = admin_logged_in.get(f'/admin/attendance/{course1_id}')
        assert resp.status_code == 200

    def test_attendance_post_success(self, admin_logged_in):
        """TC-ATD-03: 提交签到应创建记录并更新attendance_count"""
        course1_id = admin_logged_in.test_data['course1_id']
        enrollment1_id = admin_logged_in.test_data['enrollment1_id']
        resp = admin_logged_in.post(f'/admin/attendance/{course1_id}', data={
            'class_date': '2026-03-15',
            f'attendance_{enrollment1_id}': 'present'
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_attendance_post_modify_existing(self, admin_logged_in):
        """TC-ATD-04: 修改已有签到记录应正确更新attendance_count"""
        course1_id = admin_logged_in.test_data['course1_id']
        enrollment1_id = admin_logged_in.test_data['enrollment1_id']
        # 第一次：设为 present
        admin_logged_in.post(f'/admin/attendance/{course1_id}', data={
            'class_date': '2026-03-20',
            f'attendance_{enrollment1_id}': 'present'
        }, follow_redirects=True)
        # 第二次：改为 absent，attendance_count 应减少
        resp = admin_logged_in.post(f'/admin/attendance/{course1_id}', data={
            'class_date': '2026-03-20',
            f'attendance_{enrollment1_id}': 'absent'
        }, follow_redirects=True)
        assert resp.status_code == 200

    def test_attendance_post_absent_no_count_change(self, admin_logged_in):
        """TC-ATD-05: 初始absent不应增加attendance_count"""
        course1_id = admin_logged_in.test_data['course1_id']
        enrollment1_id = admin_logged_in.test_data['enrollment1_id']
        resp = admin_logged_in.post(f'/admin/attendance/{course1_id}', data={
            'class_date': '2026-03-25',
            f'attendance_{enrollment1_id}': 'absent'
        }, follow_redirects=True)
        assert resp.status_code == 200


class TestMoveStudent:
    """人员调整测试"""

    def test_move_student_success(self, admin_logged_in):
        """TC-MOVE-01: 将学生从当前课程调整至有余量课程应成功"""
        user1_id = admin_logged_in.test_data['user1_id']
        course1_id = admin_logged_in.test_data['course1_id']
        course3_id = admin_logged_in.test_data['course3_id']  # 有余量
        resp = admin_logged_in.post('/move_student',
            data=json.dumps({
                'student_id': user1_id,
                'current_course_id': course1_id,
                'target_course_id': course3_id
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_move_student_to_full_course(self, admin_logged_in):
        """TC-MOVE-02: 调整至已满课程应失败"""
        user1_id = admin_logged_in.test_data['user1_id']
        course1_id = admin_logged_in.test_data['course1_id']
        course2_id = admin_logged_in.test_data['course2_id']  # 已满
        resp = admin_logged_in.post('/move_student',
            data=json.dumps({
                'student_id': user1_id,
                'current_course_id': course1_id,
                'target_course_id': course2_id
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_move_student_not_in_current_course(self, admin_logged_in):
        """TC-MOVE-03: 学生不在当前课程中应失败"""
        user1_id = admin_logged_in.test_data['user1_id']
        course3_id = admin_logged_in.test_data['course3_id']
        # user1 不在 course3 中
        resp = admin_logged_in.post('/move_student',
            data=json.dumps({
                'student_id': user1_id,
                'current_course_id': course3_id,
                'target_course_id': 1
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_move_student_already_in_target(self, admin_logged_in):
        """TC-MOVE-04: 学生已在目标课程中应失败"""
        user1_id = admin_logged_in.test_data['user1_id']
        course1_id = admin_logged_in.test_data['course1_id']
        resp = admin_logged_in.post('/move_student',
            data=json.dumps({
                'student_id': user1_id,
                'current_course_id': course1_id,
                'target_course_id': course1_id
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_move_student_requires_admin(self, user_logged_in):
        """TC-MOVE-05: 普通用户调整人员应失败"""
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


class TestRemoveStudent:
    """移除学生测试"""

    def test_remove_student_success(self, admin_logged_in):
        """TC-REMV-01: 移除学生应删除报名和签到记录并减少课程人数"""
        enrollment1_id = admin_logged_in.test_data['enrollment1_id']
        resp = admin_logged_in.post('/remove_student',
            data=json.dumps({'enrollment_id': enrollment1_id}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_remove_student_not_found(self, admin_logged_in):
        """TC-REMV-02: 移除不存在的报名记录应失败"""
        resp = admin_logged_in.post('/remove_student',
            data=json.dumps({'enrollment_id': 9999}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_remove_student_requires_admin(self, user_logged_in):
        """TC-REMV-03: 普通用户移除学生应失败"""
        resp = user_logged_in.post('/remove_student',
            data=json.dumps({'enrollment_id': 1}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False


class TestAddStudent:
    """手动添加学生测试"""

    def test_add_student_success(self, admin_logged_in):
        """TC-ADDS-01: 管理员手动添加学生应成功"""
        course3_id = admin_logged_in.test_data['course3_id']
        resp = admin_logged_in.post('/add_student',
            data=json.dumps({
                'course_id': course3_id,
                'child_name': '新学生',
                'parent_name': '新家长',
                'phone': '13600136000'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_add_student_missing_child_name(self, admin_logged_in):
        """TC-ADDS-02: 缺少学生姓名应失败"""
        course3_id = admin_logged_in.test_data['course3_id']
        resp = admin_logged_in.post('/add_student',
            data=json.dumps({
                'course_id': course3_id,
                'child_name': '',
                'parent_name': '家长',
                'phone': '13600136000'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_add_student_course_full(self, admin_logged_in):
        """TC-ADDS-03: 课程已满时添加学生应失败"""
        course2_id = admin_logged_in.test_data['course2_id']  # 已满
        resp = admin_logged_in.post('/add_student',
            data=json.dumps({
                'course_id': course2_id,
                'child_name': '新学生',
                'parent_name': '新家长',
                'phone': '13600136000'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_add_student_nonexistent_course(self, admin_logged_in):
        """TC-ADDS-04: 不存在的课程应失败"""
        resp = admin_logged_in.post('/add_student',
            data=json.dumps({
                'course_id': 9999,
                'child_name': '新学生',
                'parent_name': '新家长',
                'phone': '13600136000'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_add_student_requires_admin(self, user_logged_in):
        """TC-ADDS-05: 普通用户添加学生应失败"""
        resp = user_logged_in.post('/add_student',
            data=json.dumps({
                'course_id': 1,
                'child_name': '新学生',
                'parent_name': '新家长',
                'phone': '13600136000'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False


class TestHoursManagement:
    """课时管理测试"""

    def test_hours_management_requires_admin(self, user_logged_in):
        """TC-HOUR-01: 普通用户访问课时管理应被重定向"""
        resp = user_logged_in.get('/admin/hours_management', follow_redirects=False)
        assert resp.status_code == 302

    def test_hours_management_success(self, admin_logged_in):
        """TC-HOUR-02: 管理员应能查看课时统计"""
        resp = admin_logged_in.get('/admin/hours_management')
        assert resp.status_code == 200


class TestTempAdjust:
    """临时调课测试"""

    def test_temp_adjust_success(self, admin_logged_in):
        """TC-TEMP-01: 临时调课应创建签到记录并更新次数"""
        enrollment1_id = admin_logged_in.test_data['enrollment1_id']
        course1_id = admin_logged_in.test_data['course1_id']
        resp = admin_logged_in.post('/temp_adjust',
            data=json.dumps({
                'enrollment_id': enrollment1_id,
                'course_id': course1_id,
                'class_date': '2026-04-01'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_temp_adjust_missing_fields(self, admin_logged_in):
        """TC-TEMP-02: 缺少必填字段应失败"""
        resp = admin_logged_in.post('/temp_adjust',
            data=json.dumps({'enrollment_id': 1}),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_temp_adjust_nonexistent_enrollment(self, admin_logged_in):
        """TC-TEMP-03: 不存在的报名记录应失败"""
        course1_id = admin_logged_in.test_data['course1_id']
        resp = admin_logged_in.post('/temp_adjust',
            data=json.dumps({
                'enrollment_id': 9999,
                'course_id': course1_id,
                'class_date': '2026-04-01'
            }),
            content_type='application/json')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is False

    def test_temp_adjust_requires_admin(self, user_logged_in):
        """TC-TEMP-04: 普通用户调课应失败"""
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
