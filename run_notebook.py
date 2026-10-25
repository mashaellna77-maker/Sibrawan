"""Execute and save the notebook with a fresh kernel, using workspace caches."""
import os
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
scratch=ROOT/'.runtime'
scratch.mkdir(exist_ok=True)
for key,folder in [('IPYTHONDIR','ipython'),('JUPYTER_CONFIG_DIR','config'),
                   ('JUPYTER_DATA_DIR','data'),('JUPYTER_RUNTIME_DIR','runtime'),('MPLCONFIGDIR','mpl')]:
    os.environ[key]=str(scratch/folder)
import nbformat
from nbclient import NotebookClient
nb=nbformat.read(ROOT/'project.ipynb',as_version=4)
t=time.perf_counter()
NotebookClient(nb,timeout=600,kernel_name='python3',resources={'metadata':{'path':str(ROOT)}}).execute()
nbformat.write(nb,ROOT/'project.ipynb')
print(f'Clean kernel completed in {time.perf_counter()-t:.2f} seconds')
