#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import socket

def get_local_ip():
    try:
        # Connect to a public server to resolve the local network interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
    
    # Custom developer startup messaging
    if len(sys.argv) > 1 and sys.argv[1] == 'runserver':
        local_ip = get_local_ip()
        print("\n==================================================================")
        print("CHIPSCAN PH - PYTHON & DJANGO FRAMEWORK LAUNCHED!")
        print("==================================================================")
        print(f"Local Computer access:   http://127.0.0.1:8000")
        print(f"Phone / Same WiFi access: http://{local_ip}:8000")
        print("==================================================================")
        print("NOTE: For camera access on your mobile phone, open Chrome and go to:")
        print("   chrome://flags/#unsafely-treat-insecure-origin-as-secure")
        print(f"   Enable it and add: http://{local_ip}:8000")
        print("==================================================================\n")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()
