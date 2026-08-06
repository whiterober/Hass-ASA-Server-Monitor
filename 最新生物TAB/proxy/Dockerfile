# ASA 最新生物 - 刷新代理（纯标准库，无 pip 依赖）
FROM python:3.12-slim

WORKDIR /app
COPY server.py .

ENV PORT=8080
EXPOSE 8080

CMD ["python", "server.py"]
