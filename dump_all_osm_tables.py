"""Dump all OSM tables from Production MySQL via SSH tunnel, then import into local MySQL.

Phase 1: mysqldump from prod (via SSH tunnel) -> .sql files
Phase 2: mysql import .sql files -> local MySQL (localhost:3307/osm_local)

Usage:
  python dump_all_osm_tables.py              # dump + import
  python dump_all_osm_tables.py --dump-only  # dump only (skip import)
  python dump_all_osm_tables.py --import-only # import only (skip dump, use existing .sql files)
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

# Production MySQL config (remote, via SSH tunnel)
PROD_MYSQL_HOST = '127.0.0.1'
PROD_MYSQL_PORT = 3306
PROD_MYSQL_USER = 'thaiphc_admin'
PROD_MYSQL_PASS = '1q2w3e4r'
PROD_MYSQL_DB = 'thaiphc_phc'

# Local MySQL config
LOCAL_MYSQL_HOST = '127.0.0.1'
LOCAL_MYSQL_PORT = 3307
LOCAL_MYSQL_USER = 'root'
LOCAL_MYSQL_PASS = '1234'
LOCAL_MYSQL_DB = 'osm_local'

# Tools
MYSQLDUMP_PATH = 'C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump'
MYSQL_PATH = 'C:/Program Files/MySQL/MySQL Server 8.0/bin/mysql'

# Dump output directory
DUMP_DIR = 'sql_dumps'

# All tables to dump (large data tables first, then master tables)
TABLES = [
    # --- Large data tables ---
    'osm_profile',
    'osm_child',
    'osm_marry',
    'osm_position',
    'osm_course',
    'osm_courses',
    'osm_best',
    'osm_enhance',
    'osm_crisis',
    'osm_result',
    'osm_scourse',
    'osm_transkill',
    'osm_occupation',
    'osm_funding',
    'osm_ability',
    'osm_ability_3',
    'osm_expert',
    'osm_excellent',
    'osm_capability_d',
    'osm_capability_h',
    'osm_picactivity',
    'osm_positioncf',
    'osm_positionosm',
    'osm_profile_pic',
    'osm_healthVolunteerCapacity',
    # --- Master/lookup tables ---
    'osm_masbestlevel',
    'osm_mascourse',
    'osm_masenhance',
    'osm_masposition',
    'osm_masprefix',
    'osm_massaka',
    'osm_masskill',
    'osm_masstudy',
    'osm_mastercourse',
]


def forward_tunnel(local_port, remote_host, remote_port, transport):
    """Create a local TCP listener that forwards to remote via SSH."""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', local_port))
    server.listen(5)
    server.settimeout(1800)  # 30 min timeout for large tables

    def handle_client(client_sock):
        try:
            chan = transport.open_channel(
                'direct-tcpip',
                (remote_host, remote_port),
                client_sock.getpeername()
            )
        except Exception as e:
            print(f'  Channel open failed: {e}')
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
        '-u', PROD_MYSQL_USER,
        f'-p{PROD_MYSQL_PASS}',
        '--default-character-set=utf8mb4',
        '--single-transaction',
        '--set-charset',
        '--hex-blob',
        '--skip-lock-tables',
        '--quick',
        '--net-buffer-length=32768',
        f'--result-file={dump_file}',
        PROD_MYSQL_DB,
        table_name,
    ]

    start = time.time()
    print(f'  [{table_name}] Dumping...')
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)

    elapsed = time.time() - start
    if result.returncode == 0:
        size = os.path.getsize(dump_file)
        print(f'  [{table_name}] OK ({size:,} bytes / {size / 1024 / 1024:.2f} MB) in {elapsed:.1f}s')
        return True
    else:
        print(f'  [{table_name}] FAILED (code={result.returncode}) in {elapsed:.1f}s')
        if result.stderr:
            print(f'    stderr: {result.stderr[:500]}')
        return False


def import_table(table_name, dump_file):
    """Import a .sql dump file into local MySQL."""
    if not os.path.exists(dump_file):
        print(f'  [{table_name}] SKIP - file not found: {dump_file}')
        return False

    size = os.path.getsize(dump_file)
    print(f'  [{table_name}] Importing {size / 1024 / 1024:.2f} MB...')

    cmd = [
        MYSQL_PATH,
        '-h', LOCAL_MYSQL_HOST,
        '-P', str(LOCAL_MYSQL_PORT),
        '-u', LOCAL_MYSQL_USER,
        f'-p{LOCAL_MYSQL_PASS}',
        '--default-character-set=utf8mb4',
        LOCAL_MYSQL_DB,
    ]

    start = time.time()
    with open(dump_file, 'r', encoding='utf-8') as f:
        result = subprocess.run(cmd, stdin=f, capture_output=True, text=True, timeout=1800)

    elapsed = time.time() - start
    if result.returncode == 0:
        print(f'  [{table_name}] OK in {elapsed:.1f}s')
        return True
    else:
        print(f'  [{table_name}] FAILED (code={result.returncode}) in {elapsed:.1f}s')
        if result.stderr:
            print(f'    stderr: {result.stderr[:500]}')
        return False


def ensure_local_db():
    """Create local database if not exists."""
    cmd = [
        MYSQL_PATH,
        '-h', LOCAL_MYSQL_HOST,
        '-P', str(LOCAL_MYSQL_PORT),
        '-u', LOCAL_MYSQL_USER,
        f'-p{LOCAL_MYSQL_PASS}',
        '-e', f'CREATE DATABASE IF NOT EXISTS `{LOCAL_MYSQL_DB}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f'WARNING: Could not create database: {result.stderr}')


def phase_dump():
    """Phase 1: Dump all tables from prod MySQL via SSH tunnel."""
    os.makedirs(DUMP_DIR, exist_ok=True)

    print('='*60)
    print('PHASE 1: DUMP FROM PRODUCTION MYSQL')
    print('='*60)

    print('Connecting to SSH...')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SSH_HOST, port=SSH_PORT, username=SSH_USER, password=SSH_PASS, timeout=30)
    transport = ssh.get_transport()
    transport.set_keepalive(30)
    print('SSH connected.')

    local_port = find_free_port()
    print(f'Starting SSH tunnel on local port {local_port} -> {PROD_MYSQL_HOST}:{PROD_MYSQL_PORT}...')
    tunnel_thread = threading.Thread(
        target=forward_tunnel,
        args=(local_port, PROD_MYSQL_HOST, PROD_MYSQL_PORT, transport),
        daemon=True
    )
    tunnel_thread.start()
    time.sleep(1)

    results = []
    total_start = time.time()
    for i, table_name in enumerate(TABLES, 1):
        dump_file = os.path.join(DUMP_DIR, f'{table_name}_dump.sql')
        print(f'\n[{i}/{len(TABLES)}]')
        ok = dump_table(table_name, dump_file, local_port)
        results.append((table_name, dump_file, ok))

    total_elapsed = time.time() - total_start
    ssh.close()

    print(f'\n--- Dump Summary ({total_elapsed:.0f}s total) ---')
    ok_count = 0
    for table_name, dump_file, ok in results:
        status = 'OK' if ok else 'FAILED'
        if ok and os.path.exists(dump_file):
            size = os.path.getsize(dump_file)
            print(f'  {table_name}: {status} ({size / 1024 / 1024:.2f} MB)')
            ok_count += 1
        else:
            print(f'  {table_name}: {status}')
    print(f'  {ok_count}/{len(TABLES)} tables dumped successfully')

    return results


def phase_import():
    """Phase 2: Import all .sql dumps into local MySQL."""
    print('\n' + '='*60)
    print('PHASE 2: IMPORT INTO LOCAL MYSQL')
    print('='*60)

    ensure_local_db()

    results = []
    total_start = time.time()
    for i, table_name in enumerate(TABLES, 1):
        dump_file = os.path.join(DUMP_DIR, f'{table_name}_dump.sql')
        print(f'\n[{i}/{len(TABLES)}]')
        ok = import_table(table_name, dump_file)
        results.append((table_name, ok))

    total_elapsed = time.time() - total_start

    print(f'\n--- Import Summary ({total_elapsed:.0f}s total) ---')
    ok_count = sum(1 for _, ok in results if ok)
    for table_name, ok in results:
        print(f'  {table_name}: {"OK" if ok else "FAILED"}')
    print(f'  {ok_count}/{len(TABLES)} tables imported successfully')

    return results


def main():
    dump_only = '--dump-only' in sys.argv
    import_only = '--import-only' in sys.argv

    if not import_only:
        phase_dump()

    if not dump_only:
        phase_import()

    print('\nDone.')


if __name__ == '__main__':
    main()
