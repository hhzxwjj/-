# 书法报名管理系统 Docker 镜像
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY app/ ./app/
COPY static/ ./static/
COPY templates/ ./templates/
COPY run.py .
COPY mysql_schema.sql .

# 暴露端口
EXPOSE 5000

# 环境变量（生产环境请覆盖）
ENV SECRET_KEY=""
ENV ADMIN_DEFAULT_PASSWORD=""
ENV USE_MYSQL="false"

# 启动命令
CMD ["python", "run.py"]
