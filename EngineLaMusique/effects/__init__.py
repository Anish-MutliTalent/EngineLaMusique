import numpy as np


def distortion(audio, gain=10.0, mix=1.0):
    """
    Heavy distortion with multi-stage clipping.
    Output is RMS-matched to input to prevent volume boost.
    """
    input_rms = np.sqrt(np.mean(audio**2)) + 1e-10 #input lvl

    boosted = audio * (gain * 0.5) # pre amp

    clipped1 = np.tanh(boosted) # pre clip

    driven = np.where(clipped1 >= 0, np.tanh(clipped1 * gain * 0.3),np.tanh(clipped1 * gain * 0.25)) # tube amp

    driven = np.clip(driven * 1.5, -1.0, 1.0) # hard clip

    driven = cabinet_filter(driven, len(audio))  # cab sim

    # RMS matching to prevent volume boost
    driven_rms = np.sqrt(np.mean(driven**2)) + 1e-10
    driven = driven * (input_rms / driven_rms)
    
    return (1 - mix) * audio + mix * driven


def cabinet_filter(audio, N):
    """Simple cabinet IR approximation using moving averages."""

    # low pass
    kernel_size = 12 # lil roundoff
    kernel = np.ones(kernel_size) / kernel_size
    filtered = np.convolve(audio, kernel, mode='same') # lpf out
    
    # mid boost
    wide_kernel = np.ones(30) / 30.0 # kinda sharp
    very_low = np.convolve(audio, wide_kernel, mode='same')
    
    # mix
    result = filtered * 0.7 + (filtered - very_low * 0.5) * 0.3
    
    # normalize
    peak = np.max(np.abs(result))
    if peak > 0:
        result = result / peak
    
    return result


# ============================================================
# CHORUS - Rich Multi-Voice
# ============================================================
def chorus(audio, fs, rate=1.5, depth_ms=3.0, mix=0.5):
    """
    Rich 4-voice chorus.
    depth_ms: increased to 3.0ms for more noticeable modulation.
    mix: 0-1. Keeps dry signal strong for clarity.
    """
    N = len(audio)
    output = np.zeros(N)
    
    # Mix dry signal
    output += audio * (1.0 - mix * 0.5)  # Keep dry slightly dominant
    
    voices = 4
    t = np.arange(N) / fs
    
    for i in range(voices):
        # Unique LFO for each voice
        v = i / float(voices)
        phase_offset = 2 * np.pi * v
        
        voice_rate = rate * (0.9 + v * 0.4)  # Wider rate spread
        voice_depth = depth_ms * (0.9 + v * 0.3)
        
        # LFO
        lfo = voice_depth * np.sin(2 * np.pi * voice_rate * t + phase_offset)
        
        # Base delay spread wider (10-30ms) for thickness
        base_delay_ms = 15.0 + v * 8.0
        delay_in_samples = ((base_delay_ms + lfo) / 1000.0 * fs)
        
        # Interpolated read
        voice_out = np.zeros(N)
        indices = np.arange(N) - delay_in_samples
        
        # Linear interpolation
        idx_int = indices.astype(int)
        frac = indices - idx_int
        
        # Valid mask
        mask = (idx_int >= 0) & (idx_int < N - 1)
        valid_indices = np.where(mask)[0]
        
        voice_out[valid_indices] = (1 - frac[valid_indices]) * audio[idx_int[valid_indices]] + \
                                   frac[valid_indices] * audio[idx_int[valid_indices] + 1]
                                   
        output += voice_out * (mix * 0.7 / voices) # Scale wet mix
    
    # Soft clip
    return np.tanh(output)


# ============================================================
# DELAY - Prominent Multi-Tap with Filtering
# ============================================================
def delay(audio, fs, delay_ms=400, feedback=0.55, mix=0.5):
    """
    Prominent analog-style delay with filtered feedback.
    feedback: 0-0.9. Higher = more repeats.
    mix: 0-1. At 0.5 the echoes are equal to dry signal.
    """
    delay_samples = int(delay_ms * fs / 1000)
    N = len(audio)
    
    # Extended buffer for feedback tails
    extended_len = N + delay_samples * 6  # Room for 6 echoes
    buf = np.zeros(extended_len)
    buf[:N] = audio
    
    # Feedback loop with LP filter on each echo (analog warmth)
    # Each echo gets darker (high frequencies decay faster)
    lp_kernel = np.array([0.2, 0.3, 0.3, 0.2])  # Gentle LP
    
    for tap in range(6):
        tap_start = delay_samples * (tap + 1)
        tap_gain = feedback ** (tap + 1)
        
        if tap_gain < 0.02:
            break  # Too quiet
        
        if tap_start < extended_len:
            echo = np.zeros(extended_len)
            end_idx = min(N + tap_start, extended_len)
            available = end_idx - tap_start
            if available > 0:
                echo_signal = audio[:available] * tap_gain
                
                # Filter: each successive echo is darker
                for _ in range(tap + 1):
                    echo_signal = np.convolve(echo_signal, lp_kernel, mode='same')
                
                echo[tap_start:tap_start + len(echo_signal)] = echo_signal
                buf += echo
    
    # Trim back to original (or slightly longer for tail)
    output_len = min(N + delay_samples * 3, extended_len)
    output = buf[:output_len]
    
    # Build dry+wet mix
    dry = np.zeros(output_len)
    dry[:N] = audio
    
    result = (1 - mix) * dry + mix * output
    
    # Soft clip to prevent overload
    result = np.tanh(result * 0.9)
    
    return result[:N]  # Return original length


# ============================================================
# REVERB - Large Hall / Cathedral
# ============================================================
def reverb(audio, fs, decay=0.7, mix=0.5):
    """
    Large Hall reverb.
    Increased delay times for larger effective room size.
    """
    N = len(audio)
    
    # ---- EARLY REFLECTIONS ----
    # Short delays simulating first bounces off walls
    early_delays_ms = [13, 19, 23, 29, 37, 43]  # Slightly larger pre-delays
    early_gains =     [0.7, 0.6, 0.5, 0.45, 0.35, 0.3]
    
    early = np.zeros(N)
    for d_ms, g in zip(early_delays_ms, early_gains):
        d = int(d_ms * fs / 1000)
        if d < N:
            early[d:] += audio[:N-d] * g
    
    # ---- LATE REVERB (Comb Filters) ----
    # Larger delays for Hall sound
    comb_delays_ms = [47.3, 53.7, 61.3, 71.9, 83.1, 93.7, 103.1, 113.3]
    
    comb_sum = np.zeros(N)
    for delay_ms in comb_delays_ms:
        d = int(delay_ms * fs / 1000)
        g = decay * (0.88 + 0.12 * np.random.random())  # Long tails
        
        buf = np.zeros(N)
        # Vectorized comb filter (faster)
        # Note: True IIR requires loop, but for block processing with decay < 1
        # we can approximate or use loop.
        # For simplicity/correctness, sticking to loop calculation but optimized
        for n in range(d, N):
            buf[n] = audio[n] + g * buf[n - d]
        
        comb_sum += buf
    
    comb_sum /= len(comb_delays_ms)
    
    # ---- ALLPASS DIFFUSERS (Increased diffusion) ----
    diffused = comb_sum
    for ap_delay_ms in [7.3, 2.7]:  # Larger allpass
        d_ap = int(ap_delay_ms * fs / 1000)
        g_ap = 0.7
        
        ap_in = diffused.copy()
        ap_out = np.zeros(N)
        
        for n in range(d_ap, N):
            ap_out[n] = -g_ap * ap_in[n] + ap_in[n - d_ap] + g_ap * ap_out[n - d_ap]
        
        diffused = ap_out
    
    # ---- MIX ----
    wet = early * 0.3 + diffused * 0.7
    
    # Gentle high-cut
    lp_kernel = np.ones(8) / 8.0
    wet = np.convolve(wet, lp_kernel, mode='same')
    
    # ADDITIVE mix: dry signal preserved at full volume, wet layered on top
    # This guarantees clarity even with heavy reverb
    return audio + mix * wet

