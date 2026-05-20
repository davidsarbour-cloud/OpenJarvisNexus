import re, subprocess, tempfile, os
html = open('Nexus9.html', encoding='utf-8').read()
# Main script
scripts = re.findall(r'<script(?![^>]*(type))[^>]*>([\s\S]*?)</script>', html)
body = scripts[0][1]
with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False, encoding='utf-8') as f:
    f.write(body); fname = f.name
r = subprocess.run(['node', '--check', fname], capture_output=True, text=True)
os.unlink(fname)
print('Main script:', 'OK' if r.returncode==0 else 'ERROR: '+r.stderr[:400])
# Module script
mod_match = re.search(r'<script[^>]+type=["\']module["\'][^>]*>([\s\S]*?)</script>', html)
if mod_match:
    mbody = mod_match.group(1)
    r2 = subprocess.run(['node', '--input-type=module', '--check'],
                        input=mbody, capture_output=True, text=True, encoding='utf-8')
    print('Module script:', 'OK' if r2.returncode==0 else 'ERROR: '+r2.stderr[:400])
