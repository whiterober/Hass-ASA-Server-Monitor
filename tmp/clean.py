import os, shutil
# Remove all pycache
for root, dirs, files in os.walk('/config'):
    if '__pycache__' in dirs:
        shutil.rmtree(os.path.join(root, '__pycache__'), ignore_errors=True)
    for f in files:
        if f.endswith('.pyc'):
            os.remove(os.path.join(root, f))
print('cleaned')
