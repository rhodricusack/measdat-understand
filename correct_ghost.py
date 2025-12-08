import numpy as np

def epi_ghost_correction_with_refs(kspace, ref_lines):
    """
    Apply EPI Nyquist ghost correction using 3 reference scans (Navigators).
    
    Parameters:
    -----------
    kspace : ndarray
        K-space data with shape [n_lin, n_channels, n_col] (complex)
    ref_lines : ndarray
        Reference line data with shape [3, n_channels, n_col] (complex)
        Expected order:
        Ref 0: Positive gradient (same as even lines)
        Ref 1: Negative gradient (same as odd lines)
        Ref 2: Positive gradient (same as even lines)
    
    Returns:
    --------
    kspace_corrected : ndarray
        Ghost-corrected k-space data
    """
    n_lin, n_channels, n_col = kspace.shape
    n_ref, _, _ = ref_lines.shape
    
    if n_ref < 3:
        raise ValueError(f"Expected 3 reference lines, got {n_ref}")

    kspace_corrected = kspace.copy()
    
    # 1. Reverse odd lines in kspace and the negative reference line (idx 1)
    #    EPI acquisitions typically flip the readout gradient for odd lines.
    #    We flip the data so everything is in the same direction before FFT.
    #    (Note: Some scanners/recon pipelines might do this early, but raw usually implies we need to do it)
    
    # Flip odd k-space lines (1, 3, 5...)
    kspace_corrected[1::2, :, :] = kspace_corrected[1::2, :, ::-1]
    
    # Flip the negative reference line (index 1) which corresponds to odd k-space lines
    ref_lines_proc = ref_lines.copy()
    ref_lines_proc[1, :, :] = ref_lines_proc[1, :, ::-1]
    
    # 2. Estimate Phase Error
    # Average the two positive reference lines (0 and 2) to match the center time of line 1
    ref_pos = (ref_lines_proc[0] + ref_lines_proc[2]) / 2.0
    ref_neg = ref_lines_proc[1]
    
    # Iterate over channels to find phase difference
    for ch in range(n_channels):
        # Extract single channel references
        # Avoid division by zero
        r_p = ref_pos[ch]
        r_n = ref_neg[ch]
        
        # Mask out low signal areas for robust phase estimation
        # (Optional but good practice: simple magnitude threshold)
        mag = (np.abs(r_p) + np.abs(r_n)) / 2
        mask = mag > (0.1 * np.max(mag))
        
        if np.sum(mask) < 10:
             # Fallback if signal is too low (noise scan?)
            continue
            
        # Compute phase difference: angle(ref_pos / ref_neg)
        # We want to align odd (neg) to even (pos) or vice versa.
        # Let's say we want to align NEG (odd) to match POS (even).
        # Diff = angle(Ref_Pos) - angle(Ref_Neg)
        # Correction for Odd = exp(+j * Diff)
        
        # Cross product angle calculation is robust: angle(A * conj(B)) = angle(A) - angle(B)
        phase_diff_ch = np.angle(r_p * np.conj(r_n))
        
        # Unwrap phase along the readout direction
        phase_unwrapped = np.unwrap(phase_diff_ch)
        
        # Fit linear model: phase_err(k) = alpha + beta * k
        # This corresponds to:
        # alpha: Constant phase offset (0th order)
        # beta:  Group delay / shift (1st order)
        # We only fit where signal is significant
        x_indices = np.arange(n_col)
        
        # Weighted simple linear regression or just fit on mask
        if np.any(mask):
            try:
                poly = np.polyfit(x_indices[mask], phase_unwrapped[mask], 1)
                phase_fit = np.polyval(poly, x_indices)
            except:
                 phase_fit = np.zeros(n_col)
        else:
            phase_fit = np.zeros(n_col)
            
        # 3. Apply Correction
        # We model the error as being split between odd and even or fully on one.
        # Commonly for EPI:
        # Even lines (0, 2...) are assumed "correct" (or reference).
        # Odd lines (1, 3...) are shifted.
        # We shift Odd lines by exp(j * phase_fit) to align with Even.
        
        correction_factor = np.exp(1j * phase_fit)
        
        # Apply only to odd lines for this channel
        kspace_corrected[1::2, ch, :] *= correction_factor

    return kspace_corrected 
