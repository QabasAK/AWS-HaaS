# Cloud-Based Honeypot-as-a-Service 🍯
A cloud-hosted honeypot system built using Cowrie on Amazon EC2, designed to attract, log, and analyze malicious behavior. Leveraging AWS services including S3, CloudWatch, Lambda, and DynamoDB, this project demonstrates proactive security through deception, analysis, and real-time monitoring.

### Architecture 
<p align="center">
   <img src="https://github.com/user-attachments/assets/59f8b68d-741d-4c80-87a1-c8c4f83013bd" alt="AWSArch" width=75%>
 </p>

<div align="center">
<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/de4ce757-52ca-45d7-addf-eef9f19d3cc9" width="40"/></td>
    <td><b>Amazon EC2</b> – Host Cowrie SSH honeypot</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/e59d81d8-f4e5-4dd9-9011-e1bdf9588b8c" width="40"/></td>
    <td><b>Amazon S3</b> – Store log files and attacker downloads</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/5e0c1a20-36d3-42a5-bae2-e02e814486ce" width="40"/></td>
    <td><b>AWS Lambda</b> – Parse logs and trigger real-time workflows</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/c461532f-242c-4620-87b2-0c089417d462" width="40"/></td>
    <td><b>Amazon DynamoDB</b> – Store parsed metadata</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/5c8f220c-def9-47e0-8c88-8f8907c9adbe" width="40"/></td>
    <td><b>Amazon CloudWatch</b> – Monitor activity and raise alarms</td>
  </tr>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/c269aca6-e99b-4d86-8964-e76fa94d6053" width="40"/></td>
    <td><b>IAM & VPC</b> – Enforce secure and isolated access</td>
  </tr>
</table>
</div>

### Deployment and Implementation

#### Deploy Honyepot on EC2

Using Ubuntu 22.04 (t3.micro) to host the honeypot (SSH/Telnet honeypot; Cowrie) on port 2222 in a specified security group (restricted to admin IP).

#### Log Collection and Cloud Upload

Cowrie logs uploaded to S3 with a Bash automation script in which sensitive logs are stored in `/cowrie/var/log/` and `/cowrie/var/lib/cowrie/downloads/`
```bash
#!/bin/bash

bucket="honeypot-logs-2025"
timestamp=$ (date +"%Y-%m-%d_%H-%M-%S")

logs_src="$ home/cowrie/var/log/cowrie/"
downloads_src="$ home/cowrie/var/lib/cowrie/downloads/"

logs_dest="s3://$ bucket/cowrie/logs/$ timestamp/"
downloads_dest="s3://$ bucket/cowrie/downloads/$ timestamp/"

echo "Uploading Cowrie logs to $ logs_dest ..."
aws s3 cp "$ logs_src" "$ logs_dest" --recursive

echo "Uploading Cowrie downloads to $ downloads_dest ..."
aws s3 cp "$ downloads_src" "$ downloads_dest" --recursive

echo "Upload complete!"
```

#### Real Time Processing

S3 triggers a Lambda function (`CowrieLogParser`) which parses cowrie logs stored in S3 and inserts them into DynamoDB showcasing session ID, timestamp, IP address and command. 

#### Monitoring and Alerts

Another Lambda function (`LogDynamoDBToCloudWatch`) streams logs to CloudWatch which alert thresholds based on repeated attacker IPs using SNS notifications.

<p align="center">
   <img src="https://github.com/user-attachments/assets/5f41b4fc-7a95-4b5a-9e97-a41484cf7510" alt="SNS" width=80%>
 </p>

### Security Measures

Various security measures include instance hosted in an isolated VPC, Principle of Least Privilege (PoLP) applies across IAM roles, S3 public access blocked and encryption and region restriction enforced.

### Testing and Evaluation 
#### Direct SSH Access
To test the Cowrie honeypot, the service was first started using the terminal by navigating to
the Cowrie directory, activating the virtual environment, and running the bin/cowrie start
command.

Once active, Cowrie listens for SSH connections on port 2222. A simulated attack was
performed locally by attempting to connect via SSH to Cowrie in the EC2 instance using:
```
$ ssh -p 2222 root@<EC2_PUBLIC_IP>
```
The command leads to a fake shell environment designed to mimic a real system. 

#### Benign Hydra
To simulate a brute-force attack in a controlled and ethical manner, a custom Python script
was developed using the Paramiko library. The script was designed to mimic tools like Hydra
by attempting multiple SSH login attempts against Cowrie.

To ensure compliance with AWS’s Acceptable Use Policy, the script was configured with a
limited list of common passwords and included a delay between each login attempt to avoid
triggering automated abuse detection systems.
```python
from paramiko import *
from time import *

target_ip = "<EC2_PUBLIC_IP>"
port = "2222"
username = "root"
passwords = ["123456", "admin", "password", "toor", "qwerty", "letmein", \
                "malak", "qabas", "cloud", "2025"]
delay = 1 

print(f"[+] Starting brute-force simulation on {target_ip}...")

for password in passwords:
    print(f"[*] Trying password: {password}")
    ssh = SSHClient()

    try:
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(target_ip, port=port, username=username, password=password, timeout=5)
    except AuthenticationException:
        print(f"[-] Failed login with '{password}' (expected)")
    except Exception as e:
        print(f"[!] Error: {e}")
    finally:
        ssh.close()
        sleep(delay)

print("[+] Simulation complete!")
```
#### Scalability 
##### PowerShell-Based TCP Flood Simulation (Consecutive)
To further evaluate the responsiveness and stability of the deployed Cowrie honeypot, a
scripted test was conducted using PowerShell on a Windows host. The goal was to simulate
repeated SSH connection attempts to the Cowrie service running on port 2222 of the EC2
instance.
```powershell
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
```
The script iterates 100 times, attempting to establish a new TCP connection to the honeypot
on each iteration. A 100 ms delay is inserted between connections to control the rate and
avoid overwhelming the client system. It was later scaled to iterate 500 times with a 1 ms
delay and then 100 times with a 0.1 ms delay.

The purpose of the script is to simulate high-speed, repeated TCP connection attempts
to test the honeypot’s ability to handle rapid and concurrent access patterns, mimicking
real-world scanner or botnet behavior.
##### Python Asynchronous Flood Testing (Concurrent)
This Python script is designed to stress-test the honeypot by rapidly initiating 5,000 asynchronous TCP connection attempts to the target IP and port within a very short timeframe.
Using Python’s asyncio module, the script creates concurrent non-blocking tasks that simulate mass scanning or brute-force behaviors commonly seen in real-world attack scenarios.
```python
import asyncio

async def flood(target_ip, target_port):
    try:
        reader, writer = await asyncio.open_connection(target_ip, target_port)
        writer.close()
        print(f"Connected to {target_ip}:{target_port}")
    except Exception as e:
        pass

async def main():
    target_ip = "<EC2_PUBLIC_IP>" 
    target_port = 2222
    # 5k connections
    tasks = [flood(target_ip, target_port) for _ in range(5000)] 
    await asyncio.gather(*tasks)

asyncio.run(main())
```
The objective is to evaluate the honeypot’s resilience, scalability, and responsiveness under high-volume connection attempts, without overwhelming system resources. This test
helps verify whether the honeypot can sustain realistic and aggressive traffic patterns while
maintaining operational stability.

<img src="https://github.com/user-attachments/assets/89d3445a-4123-4130-bf30-f5828e103ba0" alt="CloudWatch" width="60%" align="left">

This level of CPU efficiency indicates strong scalability headroom for more intense or prolonged attacks. From a networking perspective, metrics showed a sharp spike in inbound
connections, confirming successful flood activity, yet no packet loss or throttling was observed. 

This suggests the underlying virtual network infrastructure effectively handled the
burst load, and the honeypot remained operational and responsive throughout.

