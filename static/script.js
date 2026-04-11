// 收起/展开功能
function initCollapsible() {
    const collapsibleHeaders = document.querySelectorAll('.collapsible-header');
    
    collapsibleHeaders.forEach(header => {
        const content = header.nextElementSibling;
        const btn = header.querySelector('.collapse-btn');
        
        header.addEventListener('click', () => {
            content.classList.toggle('active');
            btn.classList.toggle('active');
        });
    });
}

// 页面加载完成后初始化
window.addEventListener('DOMContentLoaded', initCollapsible);

// 验证码刷新功能
function refreshCaptcha() {
    const captchaImage = document.getElementById('captcha-image');
    const timestamp = new Date().getTime();
    captchaImage.src = `/captcha?${timestamp}`;
}

// 登录模式切换功能
function switchLoginMode(mode) {
    const passwordForm = document.getElementById('password-login-form');
    const codeForm = document.getElementById('code-login-form');
    const passwordBtn = document.getElementById('password-login-btn');
    const codeBtn = document.getElementById('code-login-btn');
    
    if (mode === 'password') {
        passwordForm.style.display = 'block';
        codeForm.style.display = 'none';
        passwordBtn.classList.add('active');
        codeBtn.classList.remove('active');
    } else {
        passwordForm.style.display = 'none';
        codeForm.style.display = 'block';
        passwordBtn.classList.remove('active');
        codeBtn.classList.add('active');
    }
}

// 发送验证码功能
function sendLoginVerificationCode() {
    const phoneInput = document.getElementById('login-phone');
    const phone = phoneInput.value.trim();
    const btn = document.getElementById('login-send-code-btn');
    
    if (!phone) {
        alert('请输入手机号');
        return;
    }
    
    // 手机号格式验证
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(phone)) {
        alert('请输入正确的手机号');
        return;
    }
    
    // 禁用按钮并开始倒计时
    btn.disabled = true;
    let countdown = 60;
    btn.textContent = `${countdown}秒后重新发送`;
    
    const timer = setInterval(() => {
        countdown--;
        btn.textContent = `${countdown}秒后重新发送`;
        
        if (countdown <= 0) {
            clearInterval(timer);
            btn.disabled = false;
            btn.textContent = '获取验证码';
        }
    }, 1000);
    
    // 发送验证码请求
    fetch('/send_verification_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ phone })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('验证码已发送');
        } else {
            alert('发送失败，请重试');
            clearInterval(timer);
            btn.disabled = false;
            btn.textContent = '获取验证码';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('发送失败，请重试');
        clearInterval(timer);
        btn.disabled = false;
        btn.textContent = '获取验证码';
    });
}
