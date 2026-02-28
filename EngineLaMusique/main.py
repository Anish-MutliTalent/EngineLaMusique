import sys
import time
import threading
from EngineLaMusique.conductor import Conductor
from EngineLaMusique.audio_engine import AudioEngine

def print_banner():
    print("Commands:")
    print("  start                : START THE ENGINE")
    print("  outro                : Trigger ending sequence")
    print("  intensity <0-100>    : Set intensity level")
    print("  bpm <val>            : Set tempo")
    print("  key <C/D#/..> [maj]  : Set key (e.g., 'key A maj')")
    print("  style <name>         : Switch style (rock, pop, edm, classical)")
    print("  layer <name> <on/off>: Toggle layers (kick, bass, lead, arp...)")
    print("  section <name>       : Switch section (intro, verse, chorus, build, break)")
    print("  dist <0-100>         : Set distortion %")
    print("  delay <0-100>        : Set delay mix %")
    print("  reverb <0-100>       : Set reverb mix %")
    print("  chorus <0-100>       : Set chorus mix %")
    print("  sustain <0-100>      : Set note sustain (0=staccato, 100=legato)")
    print("  status               : Show current state")
    print("  quit                 : Exit")
    print("-" * 82)
    print(r"""                                                                                  
 _____         _            __           _____         _                _____ ___ 
|   __|___ ___|_|___ ___   |  |   ___   |     |_ _ ___|_|___ _ _ ___   |  |  |_  |
|   __|   | . | |   | -_|  |  |__| .'|  | | | | | |_ -| | . | | | -_|  |  |  |  _|
|_____|_|_|_  |_|_|_|___|  |_____|__,|  |_|_|_|___|___|_|_  |___|___|   \___/|___|
          |___|                                           |_|                            
    """)

def main():
    print_banner()
    
    conductor = Conductor()
    engine = AudioEngine(conductor)
    engine_thread = None
    
    print("Engine ready. Type 'start' to begin.")

    while True:
        try:
            cmd_line = input(">> ").strip().lower()
            if not cmd_line:
                continue
                
            parts = cmd_line.split()
            cmd = parts[0]
            
            if cmd == 'quit' or cmd == 'exit':
                print("Stopping engine...")
                engine.running = False
                break
            
            elif cmd == 'start':
                if engine_thread is None or not engine_thread.is_alive():
                    conductor.start()
                    engine_thread = threading.Thread(target=engine.start, daemon=True)
                    engine_thread.start()
                    print("Engine STARTED!")
                else:
                    print("Engine is already running.")
                    
            elif cmd == 'outro':
                print("Triggering outro sequence (Ritardando -> Fade)...")
                conductor.trigger_outro()
                
            elif cmd == 'intensity':
                if len(parts) > 1:
                    val = int(parts[1])
                    conductor.set_param('intensity', val)
                    print(f"Intensity set to {val}%")
                    
            elif cmd == 'bpm':
                if len(parts) > 1:
                    val = float(parts[1])
                    conductor.set_param('bpm', val)
                    print(f"Tempo set to {val} BPM")
                    
            elif cmd == 'key':
                if len(parts) > 1:
                    key_str = " ".join(parts[1:])
                    conductor.set_param('key', key_str)
                    print(f"Key changed to {key_str}")
                    
            elif cmd == 'layer':
                if len(parts) > 2:
                    name = parts[1]
                    state = parts[2]
                    if name in conductor.layers:
                        conductor.layers[name].active = (state == 'on')
                        print(f"Layer {name} {'enabled' if state=='on' else 'disabled'}")
                    else:
                        print(f"Unknown layer: {name}. Available: {', '.join(conductor.layers.keys())}")
                else:
                    print("Usage: layer <name> <on/off>")

            elif cmd == 'style':
                if len(parts) > 1:
                    style_name = parts[1]
                    valid = ['rock', 'pop', 'edm', 'classical']
                    if style_name in valid:
                        conductor.apply_style(style_name)
                        print(f"Style switched to: {style_name.upper()}")
                    else:
                        print(f"Unknown style. Available: {', '.join(valid)}")
                        
            elif cmd == 'dist' or cmd == 'distortion':
                if len(parts) > 1:
                    val = int(parts[1])
                    conductor.set_param('distortion', val)
                    print(f"Distortion set to {val}%")
                    
            elif cmd == 'delay':
                if len(parts) > 1:
                    val = int(parts[1])
                    conductor.set_param('delay', val)
                    print(f"Delay mix set to {val}%")
                    
            elif cmd == 'reverb':
                if len(parts) > 1:
                    val = int(parts[1])
                    conductor.set_param('reverb', val)
                    print(f"Reverb mix set to {val}%")

            elif cmd == 'chorus':
                if len(parts) > 1:
                    val = int(parts[1])
                    conductor.set_param('chorus', val)
                    print(f"Chorus mix set to {val}%")

            elif cmd == 'sustain':
                if len(parts) > 1:
                    val = int(parts[1])
                    conductor.set_param('sustain', val)
                    print(f"Sustain set to {val}%")
            
            elif cmd == 'section':
                if len(parts) > 1:
                    section = parts[1]
                    print(f"Switching to {section}...")
                    
                    if section == 'intro':
                        conductor.intensity = 0.2
                        conductor.layers['pad'].active = True
                        conductor.layers['arp'].active = True
                        conductor.layers['bass'].active = False
                        for k in ['kick','snare','hihat','rhythm','lead','harmony','riser']:
                            conductor.layers[k].active = False
                            
                    elif section == 'verse':
                        conductor.intensity = 0.4
                        conductor.layers['pad'].active = True
                        conductor.layers['bass'].active = True
                        conductor.layers['kick'].active = True
                        conductor.layers['hihat'].active = True
                        conductor.layers['snare'].active = True
                        conductor.layers['rhythm'].active = (conductor.style in ['rock', 'pop'])
                        conductor.layers['lead'].active = True
                        conductor.layers['arp'].active = False
                        conductor.layers['harmony'].active = False
                        conductor.layers['riser'].active = False
                        
                    elif section == 'chorus':
                        conductor.intensity = 0.8
                        for k in conductor.layers:
                            conductor.layers[k].active = True
                        conductor.layers['riser'].active = False
                         
                    elif section == 'build':
                        conductor.intensity = 0.7
                        conductor.layers['riser'].active = True
                        conductor.layers['snare'].active = True 
                        conductor.layers['kick'].active = True
                        conductor.layers['lead'].active = True
                        conductor.layers['harmony'].active = False
                        
                    elif section == 'break':
                        conductor.intensity = 0.1
                        conductor.layers['pad'].active = True
                        for k in ['kick','snare','hihat','rhythm','lead','harmony','arp']:
                            conductor.layers[k].active = False

            elif cmd == 'status':
                print(f"[STATUS] State: {conductor.state.upper()} | BPM: {int(conductor.bpm)}")
                print(f"  Key: {conductor.key.root_name} {conductor.key.scale_type.name}")
                print(f"  Style: {conductor.style.upper()}")
                print(f"  Intensity: {int(conductor.intensity*100)}%")
                print(f"  Distortion: {conductor.distortion_pct}%")
                print(f"  Delay: {int(conductor.delay_mix*100)}%")
                print(f"  Reverb: {int(conductor.reverb_mix*100)}%")
                print(f"  Chorus: {int(conductor.chorus_mix*100)}%")
                print(f"  Sustain: {conductor.sustain_pct}%")
                print("  Layers:")
                for k, v in conductor.layers.items():
                    print(f"    {k:10s} {'ON' if v.active else 'OFF'}")
                    
            else:
                print(f"Unknown command: '{cmd}'. Type 'status' for help.")
                
        except ValueError:
            print("Invalid value provided.")
        except KeyboardInterrupt:
            print("\nExiting...")
            engine.running = False
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
