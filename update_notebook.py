import json
import os

nb_path = '/lustre/disk/home/users/cusackrh/repos/measdat-understand/measdat-understand-cmrr-multiband.ipynb'
new_code_path = '/lustre/disk/home/users/cusackrh/repos/measdat-understand/correct_ghost.py'

# Read the new code
with open(new_code_path, 'r') as f:
    new_code = f.read()

# Read the notebook
with open(nb_path, 'r') as f:
    nb = json.load(f)

# Find the cell to replace
# We look for the cell defining "def epi_ghost_correction_with_refs"
found = False
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = ''.join(cell['source'])
        if 'def epi_ghost_correction_with_refs' in source or 'def correct_nyquist_ghost' in source:
            print("Found target cell.")
            # Replace source
            # The new code is the full script content. 
            # We might want to strip the "import numpy as np" if it's already in the notebook, 
            # but repeating it is harmless.
            
            # format as list of strings with newlines for JSON
            new_source = [line + '\n' for line in new_code.split('\n')]
            # Remove last newline char from last line if present to be clean
            if new_source and new_source[-1] == '\n':
                new_source.pop()
            
            cell['source'] = new_source
            found = True
            break

if found:
    # Save the notebook
    with open(nb_path, 'w') as f:
        json.dump(nb, f, indent=1)
    print(f"Successfully updated {nb_path}")
else:
    print("Could not find the cell defining 'epi_ghost_correction_with_refs'")
    exit(1)
