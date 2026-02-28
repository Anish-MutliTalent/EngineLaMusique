import numpy as np
from enum import Enum

class ScaleType(Enum):
    MAJOR = [0, 2, 4, 5, 7, 9, 11]
    MINOR = [0, 2, 3, 5, 7, 8, 10]
    HARMONIC_MINOR = [0, 2, 3, 5, 7, 8, 11]
    PENTATONIC_MINOR = [0, 3, 5, 7, 10]
    BLUES = [0, 3, 5, 6, 7, 10]
    DORIAN = [0, 2, 3, 5, 7, 9, 10]
    PHRYGIAN = [0, 1, 3, 5, 7, 8, 10]
    LYDIAN = [0, 2, 4, 6, 7, 9, 11]
    MIXOLYDIAN = [0, 2, 4, 5, 7, 9, 10]
    LOCRIAN = [0, 1, 3, 5, 6, 8, 10]

class ChordType(Enum):
    MAJOR = [0, 4, 7]
    MINOR = [0, 3, 7]
    DIMINISHED = [0, 3, 6]
    AUGMENTED = [0, 4, 8]
    MAJOR7 = [0, 4, 7, 11]
    MINOR7 = [0, 3, 7, 10]
    DOM7 = [0, 4, 7, 10]
    MIN7FLAT5 = [0, 3, 6, 10]
    SUS2 = [0, 2, 7]
    SUS4 = [0, 5, 7]

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
A4_FREQ = 440.0

def note_to_freq(note_name, octave=4):
    """Converts a note name (e.g., 'C#', 'Hb') to frequency."""
    key = note_name.upper()
    if key not in NOTE_NAMES:
        raise ValueError(f"Invalid note name: {note_name}")
    
    semitone_dist = NOTE_NAMES.index(key) - NOTE_NAMES.index('A')
    octave_dist = octave - 4
    total_semitones = semitone_dist + (octave_dist * 12)
    
    return A4_FREQ * (2 ** (total_semitones / 12.0))

def freq_to_midi(freq):
    return 69 + 12 * np.log2(freq / 440.0)

def midi_to_freq(midi_note):
    return 440.0 * (2 ** ((midi_note - 69) / 12.0))

class Key:
    def __init__(self, root_note='C', scale_type=ScaleType.MINOR):
        self.root_freq = note_to_freq(root_note, 4)
        self.root_name = root_note
        self.scale_type = scale_type
        self.intervals = scale_type.value
        
    def get_scale_notes(self, octaves=1):
        """Returns frequencies for the scale across octaves."""
        freqs = []
        base_midi = int(round(freq_to_midi(self.root_freq)))
        for oct in range(octaves):
            for interval in self.intervals:
                freqs.append(midi_to_freq(base_midi + interval + (oct * 12)))
        return freqs

    def get_chord(self, degree, chord_type=None, inversion=0, add_7th=False):
        """Generates frequencies for a chord at a given scale degree."""
        # This is a simplified diatonic chord generator
        # degree is 1-based index (1-7)
        if degree < 1 or degree > 7:
            raise ValueError("Degree must be 1-7")
        
        idx = degree - 1
        root_interval = self.intervals[idx]
        
        # Diatonic logic if chord_type not specified
        if chord_type is None:
            # Build thirds
            third_idx = (idx + 2) % 7
            fifth_idx = (idx + 4) % 7
            
            # Calculate semitones relative to scale root
            third_interval = self.intervals[third_idx]
            if third_idx < idx: third_interval += 12
                
            fifth_interval = self.intervals[fifth_idx]
            if fifth_idx < idx: fifth_interval += 12
            
            chord_intervals = [0, third_interval - root_interval, fifth_interval - root_interval]
            
            if add_7th:
                seventh_idx = (idx + 6) % 7
                seventh_interval = self.intervals[seventh_idx]
                if seventh_idx < idx: seventh_interval += 12
                chord_intervals.append(seventh_interval - root_interval)
                
        else:
            chord_intervals = chord_type.value
            if add_7th:
                # Naive addition of 7th to fixed types (usually implied in enum for specific types)
                # But if standard major/minor, we can try.
                # Usually standard types are Enum driven.
                pass
            
        base_midi = int(round(freq_to_midi(self.root_freq))) + root_interval
        
        midi_notes = [base_midi + interval for interval in chord_intervals]
        
        # Inversions
        for _ in range(inversion):
            midi_notes[0] += 12
            midi_notes.sort()
            
        return [midi_to_freq(m) for m in midi_notes]

class ProgressionGenerator:
    """Generates standard, pleasing chord progressions."""
    def __init__(self, key):
        self.key = key
        # Standard Pop/Rock Progressions (Degrees 1-7)
        # 1-5-6-4 (Don't Stop Believin', etc.)
        # 1-4-5-4 (Wild Thing)
        # 6-4-1-5 (Sensitive/Pop)
        # 1-6-4-5 (50s Progression)
        self.common_loops = [
            [1, 5, 6, 4],
            [6, 4, 1, 5],
            [1, 4, 1, 5],
            [1, 6, 4, 5],
            [1, 5, 2, 4], # Slight variation
        ]
        self.current_loop_idx = 0
        self.current_loop = self.common_loops[0]
        
    def next_chord(self, richness=0.0, position_in_phrase=0):
        # position_in_phrase: 0, 1, 2, 3
        
        # Change loop occasionally?
        if position_in_phrase == 0 and np.random.random() < 0.1:
            self.current_loop_idx = np.random.randint(len(self.common_loops))
            self.current_loop = self.common_loops[self.current_loop_idx]
            
        degree = self.current_loop[position_in_phrase % len(self.current_loop)]
        
        # Triads only (User requested less complexity)
        # Only add 7th on Dominant (5) if richness is high
        add_7th = False
        if degree == 5 and richness > 0.7:
            add_7th = True
            
        return self.key.get_chord(degree, add_7th=add_7th)


