html = open('Nexus9.html', encoding='utf-8').read()
lines = html.split('\n')
print('Total lines:', len(lines))
print('Line 1070-1085:')
for i,l in enumerate(lines[1069:1085],1070):
    print(f'{i}: {repr(l[:110])}')

# Find JV definition
jv_lines = [(i+1,l) for i,l in enumerate(lines) if 'const JV=' in l or 'let JV=' in l or 'JV={' in l]
print('\nJV definition:', jv_lines[:3])

# Find where module actually starts in HTML
idx = 0
found = []
tag = '<script type="module">'
while True:
    pos = html.find(tag, idx)
    if pos == -1: break
    line_num = html[:pos].count('\n') + 1
    found.append((line_num, repr(html[pos-30:pos+50])))
    idx = pos + 1
print('\nAll occurrences of <script type="module">:')
for ln, ctx in found:
    print(f'  Line {ln}: {ctx}')
