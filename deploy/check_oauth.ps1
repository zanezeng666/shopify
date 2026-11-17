Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, StartTime
Write-Output "--- out ---"
Get-Content "$env:TEMP\oauth_out.txt" -ErrorAction SilentlyContinue
Write-Output "--- err ---"
Get-Content "$env:TEMP\oauth_err.txt" -ErrorAction SilentlyContinue
