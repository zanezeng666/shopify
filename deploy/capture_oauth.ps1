$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add('http://localhost:8080/')
$listener.Start()
$ctx = $listener.GetContext()
$raw = $ctx.Request.Url.AbsoluteUri
"$raw" | Out-File -FilePath "$env:USERPROFILE\Downloads\oauth_callback_url.txt" -Encoding ascii
$html = '<html><body style="font-family:sans-serif;text-align:center;padding-top:80px;background:#f0f7f0"><h1>OK! Authorization code captured (v2)</h1><p>You can close this page and go back to the chat.</p></body></html>'
$b = [Text.Encoding]::UTF8.GetBytes($html)
$ctx.Response.ContentType = 'text/html; charset=utf-8'
$ctx.Response.ContentLength64 = $b.Length
$ctx.Response.OutputStream.Write($b, 0, $b.Length)
$ctx.Response.Close()
$listener.Stop()
