
import re
import boto3
from datetime import datetime
from urllib.parse import unquote_plus

# Connect to DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('CowrieLogs')

# Regex patterns
TIMESTAMP_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z)')
NEW_CONNECTION_PATTERN = re.compile(
    r'New connection: ([\d\.]+):\d+ \(\d+\.\d+\.\d+\.\d+:\d+\) \[session: (\w+)\]'
)
IP_PATTERN = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
AUTH_PATTERN = re.compile(r"login attempt \[b'([^']+)'/b'([^']+)'\]")
COMMAND_PATTERN = re.compile(r'(CMD|Command found):\s+(.*)', re.DOTALL)

def parse_log_line(line, current_sessions):
    entry = {
        'timestamp': None,
        'eventid': 'unknown',
        'src_ip': 'unknown',
        'session': 'unknown',
        'input': 'none',
        'command': 'none'
    }

    # Timestamp
    timestamp_match = TIMESTAMP_PATTERN.match(line)
    if timestamp_match:
        entry['timestamp'] = datetime.strptime(
            timestamp_match.group(1).rstrip('Z'),
            "%Y-%m-%dT%H:%M:%S.%f"
        ).isoformat()

    # New connection line
    new_conn_match = NEW_CONNECTION_PATTERN.search(line)
    if new_conn_match:
        src_ip = new_conn_match.group(1)
        session_id = new_conn_match.group(2)
        current_sessions[src_ip] = session_id
        entry.update({
            'eventid': 'CowrieSSHFactory',
            'src_ip': src_ip,
            'session': session_id
        })
        return entry

    # General IP
    ip_match = IP_PATTERN.search(line)
    if ip_match:
        src_ip = ip_match.group(0)
        entry['src_ip'] = src_ip
        entry['session'] = current_sessions.get(src_ip, 'unknown')

    # EventID extraction
    components = re.findall(r'\[([^\]]+)\]', line)
    if components:
        entry['eventid'] = components[-1].split('.')[-1].split('#')[0]

    # Login attempt
    if 'login attempt' in line:
        auth_match = AUTH_PATTERN.search(line)
        if auth_match:
            entry['input'] = f"{auth_match.group(1)}:{auth_match.group(2)}"

    # Command execution
    cmd_match = COMMAND_PATTERN.search(line)
    if cmd_match:
        command = cmd_match.group(2).strip()[:500]
        entry['command'] = command.replace('\n', ' ').replace('\t', ' ')

    # Skip system logs
    if any(msg in line for msg in ['Failed to import', 'Twisted Version']):
        return None

    return entry

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = unquote_plus(event['Records'][0]['s3']['object']['key'])
    
    try:
        obj = s3.get_object(Bucket=bucket, Key=key)
        lines = obj['Body'].read().decode('utf-8').splitlines()

        current_sessions = {}  # Map IPs to session IDs
        entries = []

        for line in lines:
            if not line.strip():
                continue
            try:
                parsed = parse_log_line(line, current_sessions)
                if parsed and parsed['timestamp'] and parsed['session'] != 'unknown':
                    entries.append(parsed)
            except Exception as e:
                print(f"Error processing line: {line}\n{str(e)}")

        # Batch write to DynamoDB
        with table.batch_writer() as batch:
            for entry in entries:
                batch.put_item(Item={
                    'session': entry['session'],
                    'timestamp': entry['timestamp'],
                    'src_ip': entry['src_ip'],
                    'eventid': entry['eventid'],
                    'input': entry['input'],
                    'command': entry['command']
                })

        print(f"Processed {len(entries)} entries from {key}")
        return {'statusCode': 200}

    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise e
