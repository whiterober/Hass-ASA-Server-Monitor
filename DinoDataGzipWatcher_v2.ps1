# DinoData Gzip Watcher (v2) - default path, no -Path param needed
param([string]$Path = "D:\ARK Server\DinoData")

if(-not (Test-Path $Path)){
    Write-Host "DIR NOT FOUND: $Path" -ForegroundColor Red
    exit 1
}

function Compress-Gz([string]$src){
    try{
        $size1 = (Get-Item $src).Length
        Start-Sleep -Seconds 2
        if(Test-Path $src){
            $size2 = (Get-Item $src).Length
            if($size1 -ne $size2){ Start-Sleep -Seconds 3 }
        }
        if(-not (Test-Path $src)){ return }
        $dst = "$src.gz"
        $fsIn = [System.IO.File]::OpenRead($src)
        $fsOut = [System.IO.File]::Create($dst)
        $gz = New-Object System.IO.Compression.GZipStream($fsOut, [System.IO.Compression.CompressionLevel]::Optimal)
        $fsIn.CopyTo($gz)
        $gz.Close(); $fsOut.Close(); $fsIn.Close()
        Write-Host ("OK: " + (Split-Path $src -Leaf)) -ForegroundColor Green
    }catch{
        Write-Host ("FAIL: " + $src + " - " + $_.Exception.Message) -ForegroundColor Red
    }
}

Write-Host "Compressing existing files..." -ForegroundColor Cyan
Get-ChildItem $Path -Filter *.json | ForEach-Object { Compress-Gz $_.FullName }

$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $Path
$watcher.Filter = "*.json"
$watcher.NotifyFilter = [System.IO.NotifyFilters]::LastWrite -bor [System.IO.NotifyFilters]::FileName -bor [System.IO.NotifyFilters]::Size
$watcher.EnableRaisingEvents = $true

$action = {
    Start-Sleep -Seconds 1
    Compress-Gz $Event.SourceEventArgs.FullPath
}

Register-ObjectEvent $watcher Changed -Action $action | Out-Null
Register-ObjectEvent $watcher Created -Action $action | Out-Null

try{
    while($true){ Start-Sleep -Seconds 30 }
}finally{
    $watcher.Dispose()
}
