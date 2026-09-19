import sys
import os

# Add root directory to sys.path so app and other modules can be imported
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
curr_dir = os.path.abspath(os.path.dirname(__file__))
cwd = os.getcwd()

for p in [root_dir, curr_dir, cwd, '/var/task']:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

from app import app
