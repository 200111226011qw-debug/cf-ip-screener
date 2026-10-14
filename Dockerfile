# cf-ip-screener：Cloudflare 优选 IP 筛选器（升级清单：容器化部署）
# 构建：docker build -t cf-ip-screener .
# 运行：docker run --rm -v "$PWD/result:/app/result" cf-ip-screener
#       （--watch 热重载 / 定时：docker run -d ... python main.py --watch）
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 默认跑一轮全量筛选；CI 风格用 --no-speed 避免带宽超预算
CMD ["python", "main.py"]
