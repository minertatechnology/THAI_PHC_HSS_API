"""Dump osm_child and osm_marry tables from Production MySQL via SSH tunnel.

Produces two separate SQL dump files:
  - osm_child_dump.sql
  - osm_marry_dump.sql

Usage:
  python dump_osm_child_marry.py
"""

import paramiko
import subprocess
import threading
import socket
import select
import os
import sys
import time

# SSH config
SSH_HOST = '192.168.88.186'
SSH_PORT = 22
SSH_USER = 'root'
SSH_PASS = 'qazwsx!@#456_210'

# MySQL config (remote, via SSH tunnel)
MYSQL_HOST = '127.0.0.1'
MYSQL_PORT = 3306
MYSQL_USER = 'thaiphc_admin'
MYSQL_PASS = '1q2w3e4r'
MYSQL_DB = 'thaiphc_phc'

# Tables to dump
TABLES = [
    ('osm_child', 'osm_child_dump.sql'),
    ('osm_marry', 'osm_marry_dump.sql'),
]

MYSQLDUMP_PATH = 'C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump'


def forward_tunnel(local_port, remote_host, remote_port, transport):
    """Create a local TCP listener that forwards to remote via SSH."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', local_port))
    server.listen(5)
    server.settimeout(120)

    def handle_client(client_sock):
        try:
            chan = transport.open_channel(
                'direct-tcpip',
                (remote_host, remote_port),
                client_sock.getpeername()
            )
        except Exception as e:
            print(f'Channel open failed: {e}')
            client_sock.close()
            return

        while True:
            r, w, x = select.select([client_sock, chan], [], [], 1)
            if client_sock in r:
                data = client_sock.recv(65536)
                if len(data) == 0:
                    break
                chan.sendall(data)
            if chan in r:
                data = chan.recv(65536)
                if len(data) == 0:
                    break
                client_sock.sendall(data)
        chan.close()
        client_sock.close()

    while True:
        try:
            client, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client,), daemon=True)
            t.start()
        except socket.timeout:
            break
        except Exception:
            break

    server.close()


def find_free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def dump_table(table_name, dump_file, local_port):
    """Run mysqldump for a single table via the SSH tunnel."""
    cmd = [
        MYSQLDUMP_PATH,
        '-h', '127.0.0.1',
        '-P', str(local_port),
        '-u', MYSQL_USER,
        f'-p{MYSQL_PASS}',
        '--default-character-set=utf8mb4',
        '--single-transaction',
        '--set-charset',
        '--hex-blob',
        '--skip-lock-tables',
        f'--result-file={dump_file}',
        MYSQL_DB,
        table_name,
    ]

    print(f'  Dumping {MYSQL_DB}.{table_name} -> {dump_file} ...')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode == 0:
        size = os.path.getsize(dump_file)
        print(f'  OK: {dump_file} ({size:,} bytes / {size / 1024 / 1024:.2f} MB)')
        return True
    else:
        print(f'  FAILED (code={result.returncode})')
        if result.stdout:
            print(f'  stdout: {result.stdout}')
        if result.stderr:
            print(f'  stderr: {result.stderr}')
        return False


def main():
    # 1. Connect SSH
    print('Connecting to SSH...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASS, timeout=30)
    transport = ssh.get_transport()
    print('SSH connected.')

    # 2. Start tunnel in background
    local_port = find_free_port()
    print(f'Starting SSH tunnel on local port {local_port} -> {MYSQL_HOST}:{MYSQL_PORT}...')
    tunnel_thread = threading.Thread(
        target=forward_tunnel,
        args=(local_port, MYSQL_HOST, MYSQL_PORT, transport),
        daemon=True
    )
    tunnel_thread.start()
    time.sleep(1)

    # 3. Dump each table
    results = []
    for table_name, dump_file in TABLES:
        ok = dump_table(table_name, dump_file, local_port)
        results.append((table_name, dump_file, ok))

    # 4. Summary
    print('\n=== Summary ===')
    for table_name, dump_file, ok in results:
        status = 'OK' if ok else 'FAILED'
        if ok and os.path.exists(dump_file):
            size = os.path.getsize(dump_file)
            print(f'  {table_name}: {status} ({size:,} bytes)')
        else:
            print(f'  {table_name}: {status}')

    # Cleanup
    ssh.close()
    print('Done.')


if __name__ == '__main__':
    main()
