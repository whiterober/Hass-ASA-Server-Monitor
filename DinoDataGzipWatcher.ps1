# ============================================================
# DinoData Gzip Watcher —— 监听 JSON 变化自动生成 .json.gz
# 用途：游戏服务器插件输出 cryo.json/tamed.json 后，自动 gzip
#       生成 .json.gz，Qsync 同步到 NAS 时传输的是压缩文件
#       前端请求 .json.gz（nginx 从 WebDAV 拉取 1.5MB 而非 9.8MB）
# ============================================================
# 用法（游戏服务器上，管理员 PowerShell）：
#   powershell -ExecutionPolicy Bypass -File DinoDataGzipWatcher.ps1 -Path "D:\ASA\Saved\DinoData"
# 开机自启建议：任务计划程序 → 登录时运行上面命令
# ============================================================

param([string]$Path = "")

if(-not $Path){
    Write-Host "用法: powershell -ExecutionPolicy Bypass -File DinoDataGzipWatcher.ps1 -Path `"<DinoData目录>`"" -ForegroundColor Yellow
    exit 1
}
if(-not (Test-Path $Path)){
    Write-Host "目录不存在: $Path" -ForegroundColor Red
    exit 1
}
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  DinoData Gzip Watcher" -ForegroundColor Cyan
Write-Host "  监听: $Path" -ForegroundColor Cyan
Write-Host "  Ctrl+C 退出" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

function Compress-Gz([string]$src){
    try{
        # 等文件写完：大小连续两次读取一致
        $size1 = (Get-Item $src).Length
        Start-Sleep -Seconds 2
        if(Test-Path $src){
            $size2 = (Get-Item $src).Length
            if($size1 -ne $size2){
                Start-Sleep -Seconds 3
            }
        }
        if(-not (Test-Path $src)){ return }
        $dst = "$src.gz"
        $fsIn = [System.IO.File]::OpenRead($src)
        $fsOut = [System.IO.File]::Create($dst)
        $gz = New-Object System.IO.Compression.GZipStream($fsOut, [System.IO.Compression.CompressionLevel]::Optimal)
        $fsIn.CopyTo($gz)
        $gz.Close(); $fsOut.Close(); $fsIn.Close()
        $kb = [Math]::Round((Get-Item $dst).Length / 1KB)
        Write-Host "$(Get-Date -Format 'HH:mm:ss') 已压缩: $(Split-Path $src -Leaf) -> $kb KB" -ForegroundColor Green
    }catch{
        Write-Host "$(Get-Date -Format 'HH:mm:ss') 压缩失败: $src - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# 启动时先压缩现有全部 .json
Write-Host "启动压缩现有文件..." -ForegroundColor Cyan
Get-ChildItem $Path -Filter *.json | ForEach-Object { Compress-Gz $_.FullName }

# FileSystemWatcher 监听
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $Path
$watcher.Filter = "*.json"
$watcher.NotifyFilter = [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::Size
$watcher.EnableRaisingEvents = $true

$action = {
    Start-Sleep -Seconds 1
    Compress-Gz $Event.SourceEventArgs.FullPath
}

Register-ObjectEvent $watcher "Changed" -Action $action | Out-Null
Register-ObjectEvent $watcher "Created"  -Action $action | Out-Null

try{
    while($true){ Start-Sleep -Seconds 30 }
}finally{
    $watcher.Dispose()
}
