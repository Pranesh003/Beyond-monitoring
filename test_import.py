import sys
import traceback
try:
    from backend.main import app
    print("Main app imported.")
except Exception as e:
    traceback.print_exc()
