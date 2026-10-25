"""Current personal-app tests; no Git or notebook runtime required."""
from pathlib import Path
import runpy

if __name__=='__main__':
    runpy.run_path(str(Path(__file__).with_name('test_local.py')),run_name='__main__')
