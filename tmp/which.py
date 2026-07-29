import sys
sys.path.insert(0, '/config')
import build_lovelace
print("Module file:", build_lovelace.__file__)
print("Has _srgb:", hasattr(build_lovelace, '_srgb') or '_srgb' in open(build_lovelace.__file__).read())
