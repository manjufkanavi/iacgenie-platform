#!/usr/bin/env python3
"""
parse_env.py — Read .env file and output JSON dict.
Usage: python3 parse_env.py /path/to/.env
"""
import json
import sys
import os

def parse_env_file(path):
    env = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, _, v = line.partition('=')
            v = v.strip()
            # Remove surrounding quotes
            if len(v) >= 2 and ((v[0] == '"' and v[-1] == '"') or (v[0] == "'" and v[-1] == "'")):
                v = v[1:-1]
            env[k.strip()] = v
    return env

if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ENV_PATH', '.env')
    env = parse_env_file(path)
    print(json.dumps(env))
