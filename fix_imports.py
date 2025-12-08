import json

nb_path = '/lustre/disk/home/users/cusackrh/repos/measdat-understand/measdat-understand-cmrr-multiband.ipynb'

with open(nb_path, 'r') as f:
    nb = json.load(f)

# Find first code cell
for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = cell['source']
        # Check if already imported
        already_has_numpy = False
        for line in source:
            if 'import numpy' in line:
                already_has_numpy = True
                break
        
        if not already_has_numpy:
            print("Adding 'import numpy as np' to first code cell.")
            # Insert at top
            cell['source'].insert(0, 'import numpy as np\n')
            
            with open(nb_path, 'w') as f:
                json.dump(nb, f, indent=1)
            print("Saved notebook.")
        else:
            print("Numpy already imported in first code cell.")
        break
