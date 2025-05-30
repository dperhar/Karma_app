#!/usr/bin/env python3
print("Script started")

try:
    import sys
    sys.path.insert(0, '/app')
    print("Path added")

    from services.dependencies import container
    print("Container imported")
    
    from services.external.telethon_client import TelethonClient
    print("TelethonClient imported")
    
    print("Script completed successfully")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc() 