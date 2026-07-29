import sys
sys.path.insert(0, r'b:\项目\Hass ASA Server Monitor\tmp')
import bl
src = open(bl.__file__, encoding='utf-8').read()
lines = src.split('\n')
for i in range(2030, 2060):
    print(f'{i+1}: {lines[i][:150]}')
