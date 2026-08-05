from pathlib import Path

pf = Path('/Users/manjunathkanavi/iacgenie-platform/platform/frontend/vite.config.ts')
c = pf.read_text()

# Find and fix the KNOWN_IMPORTS guard
lines = c.split('\n')
for i, line in enumerate(lines):
    if 'if (KNOWN_IMPORTS[importName])' in line and 'typeof' not in line:
        # Replace the if condition
        lines[i] = line.replace(
            'if (KNOWN_IMPORTS[importName])',
            'if (KNOWN_IMPORTS[importName] && typeof KNOWN_IMPORTS[importName] === "string")'
        )
        print(f'Fixed line {i+1}')
        break

pf.write_text('\n'.join(lines))
print('Done!')
