html = open('Nexus9.html', encoding='utf-8').read()
lines = html.split('\n')

# Find line 1061 (end of resize() function) — the last good line before corruption
# But wait — we already rebuilt once. Let's find the split point.
# The main script ends at </script> before the module.
# Find where the missing section starts (JV definition)
jv_line = next((i for i,l in enumerate(lines) if 'const JV=' in l), None)
init_line = next((i for i,l in enumerate(lines) if 'function init(' in l), None)
module_line = next((i for i,l in enumerate(lines) if '<script type="module">' in l and 'see' not in l), None)

print(f'JV at line {jv_line+1 if jv_line else "MISSING"}')
print(f'init at line {init_line+1 if init_line else "MISSING"}')
print(f'module at line {module_line+1 if module_line else "MISSING"}')

# The main script </script> is at line before module
script_end = next((i for i,l in enumerate(lines) if '</script>' in l and i < module_line), None)
print(f'</script> before module at line {script_end+1 if script_end else "MISSING"}')
