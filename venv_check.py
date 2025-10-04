import sys, traceback
print('sys.executable:', sys.executable)
print('sys.version:', sys.version)
try:
    import django
    print('Django version:', django.get_version())
except Exception:
    traceback.print_exc()