import json
import re

nb_path = '/lustre/disk/home/users/cusackrh/repos/measdat-understand/measdat-understand-cmrr-multiband.ipynb'

try:
    with open(nb_path, 'r') as f:
        nb = json.load(f)
except Exception as e:
    print(f"Error reading notebook: {e}")
    exit(1)

print(f"Inspecting cells 19 and 21 in {nb_path}")

for i, cell in enumerate(nb.get('cells', [])):
    source = cell.get('source', [])
    source_text = ''.join(source)
    
    if 'kspace_epi =' in source_text or 'def ifft2' in source_text or 'def rms_comb' in source_text:
        print(f"--- Cell {i} ({cell.get('cell_type')}) ---")
        print(source_text)
        print("\n")
