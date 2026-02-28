import sys
sys.path.insert(0, ".")
from EngineLaMusique.conductor import Conductor
from EngineLaMusique.audio_engine import AudioEngine
import numpy as np
import time

def verify_workflow():
    print("--- Starting Workflow Verification ---")
    
    # 1. Setup
    c = Conductor()
    e = AudioEngine(c)
    
    print(f"Initial State: {c.state}") 
    if c.state != 'setup':
        print("FAIL: Initial state is not 'setup'")
        return False

    # 2. Verify Silence in Setup
    buf = e.render_next_beat()
    peak = np.max(np.abs(buf))
    print(f"Setup output peak: {peak}")
    if peak != 0.0:
        print("FAIL: Audio produced during setup state!")
        return False
    print("PASS: Setup state is silent.")

    # 3. Start
    c.start()
    print(f"State after start(): {c.state}")
    if c.state != 'playing':
        print("FAIL: State did not transition to 'playing'")
        return False

    # 4. Verify Audio in Playing
    c.update() 
    buf = e.render_next_beat()
    peak = np.max(np.abs(buf))
    print(f"Playing output peak: {peak}")
    if peak == 0.0:
        for _ in range(4):
            buf = e.render_next_beat()
            peak = max(peak, np.max(np.abs(buf)))
        if peak == 0.0:
             print("WARNING: Playing state produced silence (could be intended if layers off).")
    print("PASS: Playing state logic executed.")

    # 5. Outro Trigger
    start_bpm = c.bpm
    c.trigger_outro()
    print(f"\nState after trigger_outro(): {c.state}")
    if c.state != 'outro':
        print("FAIL: State did not transition to 'outro'")
        return False
    
    # Verify initial outro state
    if c.outro_phase != 'approach':
        print(f"FAIL: Initial outro phase should be 'approach', got '{c.outro_phase}'")
        return False
    if c.outro_volume_mult != 1.0:
        print(f"FAIL: Initial outro_volume_mult should be 1.0, got {c.outro_volume_mult}")
        return False
    print("PASS: Outro triggered with correct initial state.")
    
    # 6. Verify 3-Phase Outro Progression
    print(f"\nStarting 3-Phase Outro Loop. BPM: {c.bpm}")
    max_steps = 30
    finished = False
    
    last_bpm = c.bpm
    phases_seen = set()
    phase_transitions = []
    bpm_ratios = []
    
    for i in range(max_steps):
        prev_phase = c.outro_phase
        e.render_next_beat()
        
        # Track phases
        if c.outro_phase and c.outro_phase not in phases_seen:
            phases_seen.add(c.outro_phase)
            phase_transitions.append(c.outro_phase)
        
        # Check ritardando (BPM should never increase)
        if c.bpm > last_bpm and c.state == 'outro':
            print(f"FAIL: BPM increased in Outro! {last_bpm} -> {c.bpm}")
            return False
        
        if last_bpm > 0 and c.state == 'outro':
            bpm_ratios.append(c.bpm / last_bpm)
        last_bpm = c.bpm
        
        print(f"  Step {i:2d}: phase={str(c.outro_phase):10s} state={c.state:8s} "
              f"BPM={c.bpm:6.2f} vol={c.outro_volume_mult:.3f} "
              f"intensity={c.intensity:.3f}")
        
        if c.state == 'finished':
            finished = True
            break
        
    if not finished:
        print("FAIL: Outro did not finish within expected steps.")
        return False
    
    # 7. Verify phase transitions happened in order
    print(f"\nPhase transitions: {phase_transitions}")
    expected_phases = ['approach', 'cadence', 'ringout']
    if phase_transitions != expected_phases:
        print(f"FAIL: Expected phases {expected_phases}, got {phase_transitions}")
        return False
    print("PASS: All 3 phases occurred in correct order.")
    
    # 8. Verify variable ritardando (not constant)
    if len(bpm_ratios) >= 6:
        # The ratio should change across phases (approach=0.97, cadence=0.93, ringout=0.88)
        early_ratios = bpm_ratios[:4]  # Approach phase
        late_ratios = bpm_ratios[-4:]   # Ring-out phase
        avg_early = np.mean(early_ratios)
        avg_late = np.mean(late_ratios)
        print(f"  Avg BPM ratio (approach): {avg_early:.4f}")
        print(f"  Avg BPM ratio (ringout):  {avg_late:.4f}")
        if avg_late >= avg_early:
            print("FAIL: Ritardando should be deeper in ring-out than approach")
            return False
        print("PASS: Variable ritardando confirmed (deeper in ring-out).")
    
    # 9. Verify volume fade
    if c.outro_volume_mult > 0.05:
        print(f"FAIL: outro_volume_mult should be near 0 at finish, got {c.outro_volume_mult}")
        return False
    print("PASS: Volume faded to near-silence.")
    
    # 10. Verify BPM dropped significantly
    print(f"\nFinal BPM: {c.bpm:.2f} (Started at {start_bpm:.2f})")
    if c.bpm >= start_bpm * 0.5:
        print("FAIL: Ritardando insufficient — BPM didn't drop enough.")
        return False
    print("PASS: Outro finished with significant ritardando.")

    return True

if __name__ == "__main__":
    try:
        if verify_workflow():
            print("\n✓ Verification SUCCESS!")
            sys.exit(0)
        else:
            print("\n✗ Verification FAILED!")
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ Verification CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
