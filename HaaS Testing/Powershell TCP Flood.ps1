1..100 | ForEach-Object {
  try {
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    $tcpClient.Connect("<EC2_PUBLIC_IP>", 2222)
    $tcpClient.Close()
    Write-Host "Connection $_ succeeded"
  } catch {
    Write-Host "Connection $_ failed"
  }
  Start-Sleep -Milliseconds 100
}