# 重启 OAuth 本地回调监听（先清旧进程防端口占用）
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'oauth_content_flow' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep 1
$env:PYTHONUNBUFFERED = '1'
Start-Process -FilePath python -ArgumentList 'e:\worksapce\shopify\deploy\oauth_content_flow.py' -WindowStyle Hidden `
  -RedirectStandardOutput "$env:TEMP\oauth_out.txt" -RedirectStandardError "$env:TEMP\oauth_err.txt"
Start-Sleep 4
"--- stdout ---"
Get-Content "$env:TEMP\oauth_out.txt" -ErrorAction SilentlyContinue
"--- stderr ---"
Get-Content "$env:TEMP\oauth_err.txt" -ErrorAction SilentlyContinue
