FROM python:3.11-slim

WORKDIR /app

# 轻量版和Gateway（零依赖）
COPY lightweight/ /app/lightweight/
COPY gateway/ /app/gateway/

EXPOSE 8000

# 默认运行Gateway
CMD ["python", "-m", "lightweight"]
