html = open('Nexus9.html', encoding='utf-8').read()
# Skip the comment that mentions <script type="module">
# Find the ACTUAL opening tag (not inside a comment)
idx = 0
while True:
    idx = html.find('<script type="module">', idx)
    if idx == -1: break
    # Check it's a real tag (not inside a JS string/comment)
    # Real tag: preceded by newline or whitespace
    before = html[idx-5:idx]
    if '\n' in before or before.strip() == '':
        break
    idx += 1
end_tag = html.find('</script>', idx)
print('Module start line:', html[:idx].count('\n')+1, '(char', idx, ')')
print('Module end line:', html[:end_tag+9].count('\n')+1)
print('First 100 chars of module:', repr(html[idx:idx+100]))
