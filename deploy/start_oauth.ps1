$env:T = $env:TEMP
Start-Process -FilePath python -ArgumentList 'e:\worksapce\shopify\deploy\oauth_content_flow.py' -WindowStyle Hidden -RedirectStandardOutput "$env:T\oauth_out.txt" -RedirectStandardError "$env:T\oauth_err.txt"
Start-Sleep 4
Get-Content "$env:T\oauth_out.txt"
