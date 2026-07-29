import sys, importlib
sys.path.insert(0, '/config')
sys.dont_write_bytecode = True

# Force reload from source
if 'build_lovelace' in sys.modules:
    del sys.modules['build_lovelace']

# Read source and exec directly  
src = open('/config/build_lovelace.py').read()
ns = {'__name__': 'build_lovelace', '__file__': '/config/build_lovelace.py'}
exec(src, ns)

css = ns['make_ic_css'](ns['SERVER_MAP'], ns['FIXED_STYLES_MAP'])
print("exec braces:", css.count("{"), css.count("}"))
print("exec {0}:", css.count("{0}"))
