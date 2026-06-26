# 一键禁用本项目不需要的 23 个扩展
$disable = @(
    # Java 全家桶
    "redhat.java", "vscjava.vscode-gradle", "vscjava.vscode-java-debug",
    "vscjava.vscode-java-dependency", "vscjava.vscode-java-pack",
    "vscjava.vscode-java-test", "vscjava.vscode-maven",
    # C++ 全家桶
    "ms-vscode.cmake-tools", "ms-vscode.cpptools", "ms-vscode.cpptools-extension-pack",
    "ms-vscode.cpptools-themes", "ms-vscode.cpp-devtools",
    # .NET 全家桶
    "ms-dotnettools.csdevkit", "ms-dotnettools.csharp", "ms-dotnettools.vscode-dotnet-runtime",
    # 前端框架（本项目无）
    "vue.volar",
    # 数据库（非核心）
    "cweijan.dbclient-jdbc", "cweijan.vscode-database-client2",
    # 其他无关
    "anthropic.claude-code", "dbaeumer.vscode-eslint",
    "docker.docker", "humao.rest-client", "vmware.vscode-spring-boot"
)

foreach ($ext in $disable) {
    code --disable-extension $ext 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ 已禁用: $ext" -ForegroundColor Green
    } else {
        Write-Host "✗ 跳过: $ext" -ForegroundColor Gray
    }
}
Write-Host "`n完成！已禁用 $($disable.Count) 个无关扩展" -ForegroundColor Cyan
Write-Host "如需恢复：Ctrl+Shift+X → 搜索名称 → 点 Enable" -ForegroundColor Yellow
