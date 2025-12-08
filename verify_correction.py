import twixtools
import numpy as np
import matplotlib.pyplot as plt
from correct_ghost import correct_nyquist_ghost
import sys
import os

# Set file path (hardcoded from notebook inspection)
full_sub_file_path = '/lustre/disk/home/shared/cusacklab/foundcog-raw/participants/ICC_103A/meas_MID00039_FID94271_cmrr_SBep2d_se_AP_RDS.dat'

print(f"Loading data from {full_sub_file_path}...")
try:
    twix_raw = twixtools.read_twix(full_sub_file_path)
    # Target the second measurement (Main EPI)
    mdb_list = twix_raw[1]['mdb']
    hdr = twix_raw[1]['hdr']
except Exception as e:
    print(f"Error loading data: {e}")
    sys.exit(1)

# Extract parameters
print("Extracting parameters...")
# We need to find n_channels, n_col, n_lin
# We'll scan a few MDBs to find max sizes
max_lin = 0
max_rep = 0
max_slc = 0
n_channels = 0
n_col = 0

# Scan for dimensions and separate refs vs image
image_mdbs = []
ref_mdbs = []

for mdb in mdb_list:
    if mdb.is_image_scan():
        image_mdbs.append(mdb)
        max_lin = max(max_lin, mdb.cLin)
        max_rep = max(max_rep, mdb.cRep)
        max_slc = max(max_slc, mdb.cSlc)
        if n_channels == 0 and hasattr(mdb, 'channel_hdr'):
            n_channels = len(mdb.channel_hdr)
        if n_col == 0 and hasattr(mdb, 'data'):
            # data shape is usually [channels, cols]
            n_col = mdb.data.shape[1]
            
    elif mdb.cLin == 32: # Based on notebook, ref lines are hiding here with cLin=32? OR use is_ref_scan
         # Notebook said "other scans" have cLin=32, potentially refs
         ref_mdbs.append(mdb)

n_lin = max_lin + 1
n_rep = max_rep + 1
n_slc = max_slc + 1

print(f"Dimensions: Reps={n_rep}, Slices={n_slc}, Lines={n_lin}, Channels={n_channels}, Cols={n_col}")
print(f"Found {len(ref_mdbs)} potential reference lines.")

# Let's target Representative Slope/Slice for verification
# Rep 5, Slice 10 (arbitrary middle)
target_rep = 5
target_slc = 10

print(f"Extracting data for Rep={target_rep}, Slice={target_slc}...")

# 1. Extract Image K-space
kspace_slice = np.zeros((n_lin, n_channels, n_col), dtype=np.complex64)
filled_lines = 0

for mdb in image_mdbs:
    if mdb.cRep == target_rep and mdb.cSlc == target_slc:
        line = mdb.cLin
        if line < n_lin:
            kspace_slice[line, :, :] = mdb.data
            filled_lines += 1

print(f"Filled {filled_lines}/{n_lin} k-space lines.")

# 2. Extract Reference Lines
# Need to find the 3 refs for this slice/rep
# Notebook logic: "They appear in order for each slice"
# We need to filter ref_mdbs for this slice/rep
ref_slice = []
for mdb in ref_mdbs:
    if mdb.cRep == target_rep and mdb.cSlc == target_slc:
        ref_slice.append(mdb)

# Sort strictly by acquisition order if needed, but usually list order is acq order
# We expect 3 lines
if len(ref_slice) != 3:
    print(f"Warning: Found {len(ref_slice)} ref lines for this slice (expected 3).")
    if len(ref_slice) < 3:
        print("Cannot proceed with verification for this slice.")
        sys.exit(1)

ref_data = np.zeros((3, n_channels, n_col), dtype=np.complex64)
for i in range(3):
    ref_data[i, :, :] = ref_slice[i].data

print("Data extraction complete.")

# --- PROCESSING ---

def reconstruct(ksp):
    return np.fft.ifft2(ksp)

def combine(img):
    # RMS combination
    return np.sqrt(np.sum(np.abs(img)**2, axis=0))

# 1. Naive Reconstruction (No Flip, No Phase Corr)
print("Reconstructing Naive...")
img_naive = combine(reconstruct(kspace_slice))

# 2. Flip Only (Manual Flip odd lines)
print("Reconstructing Flip Only...")
kspace_flip = kspace_slice.copy()
kspace_flip[1::2, :, :] = kspace_flip[1::2, :, ::-1]
img_flip = combine(reconstruct(kspace_flip))

# 3. Full Correction
print("Reconstructing Corrected...")
try:
    kspace_corr = correct_nyquist_ghost(kspace_slice, ref_data)
    img_corr = combine(reconstruct(kspace_corr))
except Exception as e:
    print(f"Correction failed: {e}")
    sys.exit(1)

# --- VISUALIZATION ---
fig, axes = plt.subplots(1, 3, figsize=(15, 5))

def show_img(ax, img, title):
    # crop to center for better view
    # h, w = img.shape
    # cy, cx = h//2, w//2
    # dy, dx = h//4, w//4
    # img_crop = img[cy-dy:cy+dy, cx-dx:cx+dx]
    
    # Simple normalization
    disp = np.abs(img)
    p99 = np.percentile(disp, 99)
    ax.imshow(disp, cmap='gray', vmin=0, vmax=p99)
    ax.set_title(title)
    ax.axis('off')

show_img(axes[0], img_naive, "Naive (No Corr)")
show_img(axes[1], img_flip, "Flip Only (No Phase)")
show_img(axes[2], img_corr, "Full Ghost Constrection")

out_path = '/lustre/disk/home/users/cusackrh/.gemini/antigravity/brain/6414c150-8319-4619-9115-8712343ea30d/verification_result.png'
plt.savefig(out_path)
print(f"Saved comparison to {out_path}")
