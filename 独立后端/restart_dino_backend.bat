@echo off
REM 重启 dino_backend 计划任务（Stop + Start）
chcp 65001 >nul
echo [1/2] 停止 dino_backend...
powershell -NoProfile -Command "Stop-ScheduledTask -TaskName dino_backend"
echo [2/2] 启动 dino_backend...
powershell -NoProfile -Command "Start-ScheduledTask -TaskName dino_backend"
echo 完成：dino_backend 已重启
