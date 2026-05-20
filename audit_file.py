html = open('Nexus9.html', encoding='utf-8').read()
lines = html.split('\n')
print(f'Total lines: {len(lines)}')

# Check key functions present
checks = ['safeInit','function init(','const JV=','function jvSay','function resize()',
          'STL_AIDS','STL_PIPE','function startMission','function wakeJarvis',
          'function tick(','function fetchBizData','function buildAgents',
          'quickReport','toggleMic','sendVoiceText','jarvisReport']
for k in checks:
    found = [(i+1) for i,l in enumerate(lines) if k in l]
    print(f'  {k}: {"lines "+str(found[:3]) if found else "MISSING"}')

# Show how many module scripts there are
mods = [i+1 for i,l in enumerate(lines) if '<script type="module">' in l and 'see' not in l]
print(f'\nModule script tags at lines: {mods}')
# Show end of main script
script_end = [i+1 for i,l in enumerate(lines) if '</script>' in l]
print(f'</script> tags at lines: {script_end[:5]}')
