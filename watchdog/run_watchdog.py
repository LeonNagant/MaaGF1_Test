"""
Watchdog runner script
Simple script to run the watchdog service
"""
import os
import sys

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from main import main

if __name__ == '__main__':
    main()