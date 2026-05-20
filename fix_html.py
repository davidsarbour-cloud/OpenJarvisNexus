html = open('Nexus9.html', encoding='utf-8').read()

# The problem: the module was inserted at the comment position inside the main script
# We need to:
# 1. Find the main <script> block and clean out the injected module
# 2. Find where the actual <script type="module"> tag starts
# 3. Reconstruct the file properly

# Find the main script block (the big non-module script)
main_script_start = html.find("<script>")
main_script_end   = html.find("</script>", main_script_start) + len("</script>")

main_script_content = html[main_script_start:main_script_end]

# Find the module tag inside the main script content (incorrectly placed)
bad_tag = '<script type="module">'
bad_pos = main_script_content.find(bad_tag)
if bad_pos != -1:
    print(f"Found misplaced module at position {bad_pos} in main script")
    # Cut main script at the bad injection point (keep comment line before it)
    # Find the comment line that precedes the injection
    comment_line = main_script_content.rfind('\n', 0, bad_pos)
    clean_main_content = main_script_content[:comment_line]
    # Find the end of this injected module inside the main script
    # Look for </script> after the bad_tag
    bad_end = main_script_content.find('</script>', bad_pos) + len('</script>')
    rest_after_injection = main_script_content[bad_end:]
    print(f"Rest after injection starts with: {repr(rest_after_injection[:80])}")
else:
    print("No misplaced module found in main script")
    clean_main_content = main_script_content
    rest_after_injection = ''

# Build the correct main script (without injected module)
# The comment about Three.js should stay
comment = '\n/* canvas 2D replaced by Three.js module — see module script below */\n'

# Find stuff after main_script_end (the rest of the HTML: forms, etc.)
after_main = html[main_script_end:]
# But if module was injected, rest_after_injection has remaining main script content
if rest_after_injection.strip():
    # The rest_after_injection is the tail of the main script (safeInit, etc.)
    # It starts with </script> which we already consumed
    # We need to put it back as part of main script
    print(f"Tail of main script: {repr(rest_after_injection[:200])}")

# Let's look at what's AFTER main_script_end in after_main
print(f"\nAfter main script (first 200): {repr(after_main[:200])}")
print(f"\nTotal file length: {len(html)}")
print(f"Main script: {main_script_start}-{main_script_end}")
