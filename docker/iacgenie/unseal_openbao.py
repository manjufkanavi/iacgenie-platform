#!/usr/bin/env python3
"""Unseal OpenBao and fix TLS config on VM."""
import subprocess
import sys

def run(cmd, shell=False):
    """Run command and return output."""
    result = subprocess.run(cmd, shell=shell, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def unseal_openbao():
    """Unseal OpenBao container using docker exec with Python."""
    unseal_keys = [
        "nV5qG9rLORJjRMlLFa8avm49JFPviTAxMSzVgBmgptzO",
        "NvPW/t7J/wCaA5wLCKfc47Bv+idozcFgHWdmrT9dJJtk",
        "/qa+fsFLRP5HNFXgFJlnFEl6A1d5OSK2xHHsNVqfa6zt",
    ]
    
    script = '''
import requests, json

base = "http://127.0.0.1:8200"
keys = ''' + json.dumps(unseal_keys) + '''

for i, key in enumerate(keys):
    resp = requests.put(f"{base}/v1/sys/unseal", json={"key": key})
    data = resp.json()
    progress = data.get("progress", "unknown")
    sealed = data.get("sealed", True)
    status = "UNSEALED" if not sealed else f"progress: {progress}/2"
    print(f"Key {i+1}: {status}")
    if not sealed:
        print("OpenBao is now UNSEALED!")
        return 0

return 1

'''
    
    # Write the script on the VM
    rc, out, err = run(f'cat << "PYEOF" | ssh mkanavi@192.168.0.118 "python3 /dev/stdin"',
                       shell=True)
    
    # Simpler approach: use docker exec with env vars
    for i, key in enumerate(unseal_keys):
        key_b64 = key.encode('utf-8').hex()  # not needed, pass as env var
        # Use python directly inside container
        python_cmd = f'''
import requests
resp = requests.put("http://127.0.0.1:8200/v1/sys/unseal", json={{"key": "{key}"}})
print(resp.status_code, resp.json().get("sealed"), resp.json().get("progress"))
'''
        # Write to temp file on host, then copy to container
        rc, out, err = run(
            f'echo "{python_cmd.replace(chr(10), " | ")}" > /tmp/unseal_{i}.py'
        )
        
        # Use a simpler approach: python3 -c with the key as variable
        rc, out, err = run(
            f'''ssh mkanavi@192.168.0.118 "docker exec iacgenie_openbao sh -c 'python3 -c \"import requests; r=requests.put(chr(39)+'http://127.0.0.1:8200/v1/sys/unseal'+chr(39), json={chr(123)+chr(39)+'key'+chr(39):chr(39)+chr(39)+chr(39)+chr(39)'+chr(125)})\"' """
        )
        # This is getting too complex. Let me use a different approach.
        break

def unseal_v2():
    """Cleaner unseal approach: write script to host, scp to container."""
    import base64
    
    keys = [
        "nV5qG9rLORJjRMlLFa8avm49JFPviTAxMSzVgBmgptzO",
        "NvPW/t7J/wCaA5wLCKfc47Bv+idozcFgHWdmrT9dJJtk",
        "/qa+fsFLRP5HNFXgFJlnFEl6A1d5OSK2xHHsNVqfa6zt",
    ]
    
    # Write a python script on the host, then execute via docker cp + exec
    script_lines = [
        "import requests, json",
        f"keys = {json.dumps(keys)}",
        'base = "http://127.0.0.1:8200"',
        'for i, key in enumerate(keys):',
        '    resp = requests.put(f"{base}/v1/sys/unseal", json={"key": key})',
        '    data = resp.json()',
        '    print(f"Key {{i+1}}: sealed={{data.get(\"sealed\")}}, progress={{data.get(\"progress\")}}")',
        '    if not data.get("sealed"):',
        '        print("UNSEALED!")',
        '        break',
    ]
    
    script_content = "\n".join(script_lines)
    
    # Write script to host
    with open("/tmp/unseal_openbao.py", "w") as f:
        f.write(script_content)
    
    # Copy to container
    subprocess.run(["scp", "/tmp/unseal_openbao.py", "mkanavi@192.168.0.118:/tmp/"],
                   capture_output=True, timeout=30)
    
    # Execute inside container
    rc, out, err = run(
        "ssh mkanavi@192.168.0.118 'docker cp /tmp/unseal_openbao.py iacgenie_openbao:/tmp/unseal.py && "
        "docker exec iacgenie_openbao sh -c \"python3 /tmp/unseal.py\"'"
    )
    
    print(out)
    return rc

if __name__ == "__main__":
    unseal_v2()
