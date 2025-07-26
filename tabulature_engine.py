# tabulature_engine.py - Streamlit-optimized version

from pydub import AudioSegment
import librosa
import numpy as np
import pretty_midi
import miditoolkit
from random import randint
from music21 import stream, note, tempo, midi
import os
import tempfile
import streamlit as st

class TabulatureEngine:
    """Streamlit-optimized tabulature engine"""
    
    def __init__(self):
        self.string_midi = [64, 59, 55, 50, 45, 40]  # Standard tuning EADGBE
        self.string_names = ["E", "B", "G", "D", "A", "E"]
        
    @st.cache_data
    def transcribe_audio_to_tab(_self, audio_bytes, filename, max_notes=25):
        """
        Streamlit-optimized audio-to-tab transcription
        Uses st.cache_data for performance
        """
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{filename.split('.')[-1]}") as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_path = tmp_file.name
            
            try:
                # Auto-detect format and convert to WAV
                audio_format = filename.split('.')[-1].lower()
                if audio_format == 'm4a':
                    audio_format = 'mp4'  # pydub uses mp4 for m4a
                
                audio = AudioSegment.from_file(tmp_path, format=audio_format)
                
                # Convert to WAV in memory
                wav_buffer = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                audio.export(wav_buffer.name, format="wav")
                
                # Load and analyze audio
                y, sr = librosa.load(wav_buffer.name)
                
                # Use onset detection for better note timing
                onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
                
                # Extract pitches using multiple methods for better accuracy
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr, threshold=0.1)
                
                midi_notes = []
                for onset_frame in onset_frames[:max_notes]:
                    # Get pitch at onset
                    if onset_frame < pitches.shape[1]:
                        idx = magnitudes[:, onset_frame].argmax()
                        pitch = pitches[idx, onset_frame]
                        if pitch > 0:
                            midi_note = int(round(librosa.hz_to_midi(pitch)))
                            if 40 <= midi_note <= 84:  # Extended guitar range
                                midi_notes.append(midi_note)
                
                # Remove duplicate consecutive notes
                cleaned_notes = []
                for note in midi_notes:
                    if not cleaned_notes or abs(note - cleaned_notes[-1]) > 1:
                        cleaned_notes.append(note)
                
                # Clean up temp files
                os.unlink(wav_buffer.name)
                
                return _self._create_tab_display(cleaned_notes), None
                
            finally:
                # Clean up original temp file
                os.unlink(tmp_path)
                
        except Exception as e:
            return None, f"Error processing audio: {str(e)}"
    
    def _create_tab_display(self, midi_notes):
        """Create formatted guitar tablature display"""
        if not midi_notes:
            return "No notes detected in audio file."
        
        tab_lines = [f"{name}|" for name in self.string_names]
        
        for note in midi_notes:
            placed = False
            for i, base_midi in enumerate(self.string_midi):
                fret = note - base_midi
                if 0 <= fret <= 24 and not placed:  # Extended to 24 frets
                    if fret < 10:
                        tab_lines[i] += f"-{fret}-"
                    else:
                        tab_lines[i] += f"{fret}-"
                    placed = True
                else:
                    tab_lines[i] += "---"
            
            if not placed:
                # Note out of range - try to place on closest string
                closest_string = min(range(6), key=lambda i: abs(note - self.string_midi[i]))
                fret = note - self.string_midi[closest_string]
                if fret > 24:
                    # Replace last segment with out-of-range notation
                    tab_lines[closest_string] = tab_lines[closest_string][:-3] + f"({fret})"
        
        return "\n".join(tab_lines)
    
    def interpret_prompt(self, prompt):
        """Enhanced prompt interpretation with more musical styles"""
        prompt = prompt.lower()
        
        # Determine style
        if "blues" in prompt:
            style = "blues"
        elif "country" in prompt or "outlaw" in prompt:
            style = "country"
        elif "rock" in prompt or "metal" in prompt:
            style = "rock"
        elif "jazz" in prompt:
            style = "jazz"
        elif "folk" in prompt or "acoustic" in prompt:
            style = "folk"
        elif "classical" in prompt:
            style = "classical"
        else:
            style = "rock"
        
        # Determine key
        if "dark" in prompt or "minor" in prompt or "sad" in prompt:
            if "blues" in prompt:
                key = "A minor"
            else:
                key = "E minor"
        elif "bright" in prompt or "major" in prompt or "happy" in prompt:
            key = "C major"
        elif "blues" in prompt:
            key = "E minor"  # Blues-friendly key
        else:
            key = "C major"
        
        # Determine tempo based on style and descriptors
        if "slow" in prompt or "ballad" in prompt:
            base_tempo = 60
        elif "fast" in prompt or "quick" in prompt:
            base_tempo = 140
        elif "medium" in prompt:
            base_tempo = 100
        else:
            # Style-based defaults
            tempo_ranges = {
                "blues": (70, 90),
                "country": (90, 120),
                "rock": (110, 140),
                "jazz": (100, 130),
                "folk": (80, 110),
                "classical": (80, 120)
            }
            tempo_range = tempo_ranges.get(style, (90, 120))
            base_tempo = randint(tempo_range[0], tempo_range[1])
        
        # Detect tuning
        tuning = "standard"
        if "drop d" in prompt or "drop-d" in prompt:
            tuning = "drop_d"
        elif "open" in prompt:
            tuning = "open_g"
        
        return {
            "style": style,
            "key": key,
            "tempo": base_tempo,
            "tuning": tuning
        }
    
    @st.cache_data
    def generate_midi(_self, music_info, num_measures=4):
        """Generate MIDI based on interpreted prompt with caching"""
        try:
            s = stream.Stream()
            s.append(tempo.MetronomeMark(number=music_info['tempo']))
            
            # Extended scale patterns for different styles
            scale_patterns = {
                "C major": ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"],
                "E minor": ["E3", "F#3", "G3", "A3", "B3", "C4", "D4", "E4"],
                "A minor": ["A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4"]
            }
            
            # Style-specific rhythm patterns (in quarter note lengths)
            rhythm_patterns = {
                "blues": [0.75, 0.25, 0.5, 0.5, 1.0],  # Swing feel
                "country": [0.5, 0.5, 0.25, 0.25, 0.5, 0.5],  # Country strumming
                "rock": [0.25, 0.25, 0.5, 0.25, 0.25, 0.5],  # Rock rhythm
                "jazz": [0.33, 0.33, 0.34, 0.5, 0.5],  # Jazz swing
                "folk": [0.5, 0.5, 0.5, 0.5],  # Simple folk
                "classical": [0.25, 0.25, 0.25, 0.25, 0.5, 0.5]  # Classical
            }
            
            notes_list = scale_patterns.get(music_info['key'], scale_patterns["C major"])
            rhythm = rhythm_patterns.get(music_info['style'], rhythm_patterns["rock"])
            
            # Generate melody with some musical logic
            previous_note_idx = randint(0, len(notes_list) - 1)
            
            for measure in range(num_measures):
                for duration in rhythm:
                    # Add some musical movement (prefer steps over jumps)
                    movement = randint(-2, 2)
                    next_note_idx = max(0, min(len(notes_list) - 1, previous_note_idx + movement))
                    
                    selected_note = notes_list[next_note_idx]
                    n = note.Note(selected_note)
                    n.quarterLength = duration
                    s.append(n)
                    
                    previous_note_idx = next_note_idx
            
            # Create temporary MIDI file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp_file:
                midi_path = tmp_file.name
            
            # Export MIDI
            mf = midi.translate.streamToMidiFile(s)
            mf.open(midi_path, 'wb')
            mf.write()
            mf.close()
            
            return midi_path, None
            
        except Exception as e:
            return None, f"Error generating MIDI: {str(e)}"
    
    @st.cache_data
    def midi_to_tab(_self, midi_bytes, filename):
        """Convert MIDI bytes to guitar tablature with caching"""
        try:
            # Create temporary file from bytes
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mid') as tmp_file:
                tmp_file.write(midi_bytes)
                midi_path = tmp_file.name
            
            try:
                midi_file = miditoolkit.midi.parser.MidiFile(midi_path)
                
                if not midi_file.instruments:
                    return None, "No instruments found in MIDI file"
                
                notes = sorted(midi_file.instruments[0].notes, key=lambda n: n.start)
                
                if not notes:
                    return None, "No notes found in MIDI file"
                
                # Convert to MIDI note numbers and create tab
                midi_notes = [note.pitch for note in notes[:30]]  # Limit for readability
                tab_result = _self._create_tab_display(midi_notes)
                
                return tab_result, None
                
            finally:
                # Clean up temp file
                os.unlink(midi_path)
                
        except Exception as e:
            return None, f"Error processing MIDI: {str(e)}"
    
    def generate_tab_from_text(self, prompt, num_measures=4):
        """Complete workflow: text -> MIDI -> tab"""
        try:
            # Interpret the prompt
            music_info = self.interpret_prompt(prompt)
            
            # Generate MIDI
            midi_path, error = self.generate_midi(music_info, num_measures)
            if error:
                return None, music_info, error
            
            try:
                # Convert MIDI to tab
                with open(midi_path, 'rb') as f:
                    midi_bytes = f.read()
                
                tab_result, error = self.midi_to_tab(midi_bytes, "generated.mid")
                if error:
                    return None, music_info, error
                
                return tab_result, music_info, None
                
            finally:
                # Clean up MIDI file
                if os.path.exists(midi_path):
                    os.unlink(midi_path)
                
        except Exception as e:
            return None, None, f"Error in text-to-tab workflow: {str(e)}"
    
    def save_tab_to_file(self, tab_content, music_info=None, filename="guitar_tab.txt"):
        """Save tablature to text file with metadata"""
        try:
            content = "Guitar Tablature\n"
            content += "================\n\n"
            
            if music_info:
                content += f"Style: {music_info.get('style', 'Unknown')}\n"
                content += f"Key: {music_info.get('key', 'Unknown')}\n"
                content += f"Tempo: {music_info.get('tempo', 'Unknown')} BPM\n"
                content += f"Tuning: {music_info.get('tuning', 'standard')}\n\n"
            
            content += tab_content
            content += "\n\nGenerated by TabGenius"
            
            return content
            
        except Exception as e:
            return f"Error formatting tab: {str(e)}"

# Initialize the engine for Streamlit
@st.cache_resource
def get_tabulature_engine():
    """Cached tabulature engine instance"""
    return TabulatureEngine()