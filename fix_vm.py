from pathlib import Path
import re

pf = Path('/home/iacgenie/iacgenie-platform/platform/frontend')
fixes = 0

for f in pf.rglob('*.tsx'):
    if 'node_modules' in str(f):
        continue
    
    data = f.read_bytes()
    original = data
    
    # Fix: from './X['\"]; → from './X';
    # The ['\"]; pattern appears when regex replaced quotes incorrectly
    text = data.decode('utf-8', errors='replace')
    
    # Simple approach: find any '...' that has extra characters after the path
    # Pattern: from './X[' ... ]; → from './X';
    new_text = re.sub(
        r"from '(\./[^'\s\[\]+)']\[.*?'\\\".;]+",
        r"from '\1';",
        text
    )
    
    # Also handle: from './NAME['\"];
    new_text = re.sub(
        r"from '(\./[^'\s]+?)\['[^']*'\];",
        r"from '\1';",
        new_text
    )
    
    # Fix bracket paths: ./ui/DeploymentPreviewModal → fix any double-segment
    # Remove duplicated module names: ./services/X/services/X → ./services/X
    new_text = re.sub(
        r"from '(\./[^'/]+/)([^'/]+)/\2\['[^']*'\];",
        r"from '\1\2';",
        new_text
    )
    
    if new_text != text:
        f.write_bytes(new_text.encode('utf-8'))
        fixes += 1

print(f'Files fixed: {fixes}')

# Verify remaining broken lines
for f in pf.rglob('*.tsx'):
    if 'node_modules' in str(f):
        continue
    c = f.read_text()
    for line in c.split('\n'):
        if 'from' in line and '[' in line and "'" in line:
            print(f'  STILL BROKEN: {f.relative_to(pf)}: {line.strip()[:120]}')
