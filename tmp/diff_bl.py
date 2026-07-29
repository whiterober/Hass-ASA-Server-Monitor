import difflib

old_src = open(r'B:\项目\Hass ASA Server Monitor\bak\baseline_20260728_201437\build_lovelace.py', encoding='utf-8').read()
new_src = open(r'B:\项目\Hass ASA Server Monitor\bak\baseline_20260729_155105\build_lovelace.py', encoding='utf-8').read()

# Extract make_ic_css function from both
old_start = old_src.find('def make_ic_css')
new_start = new_src.find('def make_ic_css')
old_end = old_src.find('\ndef ', old_start+1)
new_end = new_src.find('\ndef ', new_start+1)

old_func = old_src[old_start:old_end]
new_func = new_src[new_start:new_end]

old_lines = old_func.split('\n')
new_lines = new_func.split('\n')

diff = list(difflib.unified_diff(old_lines, new_lines, 
    fromfile='20260728 (clean)', tofile='20260729 (buggy)',
    lineterm='', n=1))

# Only show changed/added lines
for line in diff:
    if line.startswith(('+', '-', '@@')):
        print(line[:150])
