import json
import time
from backend.config import LOG_FILE
from backend.database import get_db_status, append_log_db, get_logs_db


def append_log(plant: str, filename: str, action: str, status: str, latency_ms: int = 0):
    log_entry = {
        'timestamp': int(time.time() * 1000),
        'plant': plant,
        'filename': filename,
        'action': action,
        'status': status,
        'latency_ms': latency_ms,
    }

    db_status = get_db_status()
    if db_status['enabled']:
        try:
            append_log_db(log_entry)
            return
        except Exception as e:
            print(f'Error writing DB log: {e}')

    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        print(f'Error writing to log: {e}')


def get_logs(limit: int = 100):
    db_status = get_db_status()
    if db_status['enabled']:
        try:
            return get_logs_db(limit)
        except Exception as e:
            print(f'Error reading DB logs: {e}')

    logs = []
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    logs.append(json.loads(line))
        return logs[-limit:][::-1]
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f'Error reading logs: {e}')
        return []
