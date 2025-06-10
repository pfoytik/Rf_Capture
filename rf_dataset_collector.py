#!/usr/bin/env python3
"""
RF Environment Dataset Collection System
Systematically captures RF environment data across frequencies, times, and locations
"""

import uhd
import numpy as np
import argparse
import time
import sys
import os
import json
import threading
import queue
import multiprocessing
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import subprocess

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

class DatasetCollector:
    """Manages systematic RF dataset collection"""
    
    def __init__(self, config_file=None):
        self.config = self.load_config(config_file)
        self.usrp = None
        self.collection_log = []
        
    def load_config(self, config_file):
        """Load collection configuration"""
        
        # Default configuration
        default_config = {
            "frequencies": {
                "wifi_2_4_ghz": [
                    {"name": "ch1", "freq": 2.412e9, "description": "WiFi Channel 1"},
                    {"name": "ch6", "freq": 2.437e9, "description": "WiFi Channel 6"},
                    {"name": "ch11", "freq": 2.462e9, "description": "WiFi Channel 11"},
                    {"name": "center", "freq": 2.44e9, "description": "2.4GHz Center"}
                ],
                "wifi_5_ghz": [
                    {"name": "ch36", "freq": 5.18e9, "description": "WiFi Channel 36"},
                    {"name": "ch100", "freq": 5.5e9, "description": "WiFi Channel 100"},
                    {"name": "ch149", "freq": 5.745e9, "description": "WiFi Channel 149"}
                ],
                "other_bands": [
                    {"name": "fm_radio", "freq": 100.1e6, "description": "FM Radio"},
                    {"name": "ism_433", "freq": 433.92e6, "description": "433MHz ISM"},
                    {"name": "ism_868", "freq": 868e6, "description": "868MHz ISM"},
                    {"name": "cellular_850", "freq": 850e6, "description": "Cellular 850MHz"}
                ]
            },
            "capture_settings": {
                "sample_rates": [1e6, 2e6, 5e6],  # Test different rates
                "durations": [60, 300, 900],      # 1min, 5min, 15min
                "gains": [20, 30, 40],            # Different gain settings
                "compression": "zstd",
                "compression_level": 3
            },
            "collection_modes": {
                "quick_survey": {
                    "sample_rate": 1e6,
                    "duration": 60,
                    "gain": 30
                },
                "detailed_capture": {
                    "sample_rate": 2e6,
                    "duration": 300,
                    "gain": 30
                },
                "long_term": {
                    "sample_rate": 1e6,
                    "duration": 1800,
                    "gain": 30
                }
            },
            "scheduling": {
                "time_slots": [
                    {"name": "morning", "start": "06:00", "end": "09:00"},
                    {"name": "midday", "start": "11:00", "end": "14:00"},
                    {"name": "evening", "start": "18:00", "end": "21:00"},
                    {"name": "night", "start": "23:00", "end": "02:00"}
                ]
            }
        }
        
        if config_file and os.path.exists(config_file):
            with open(config_file, 'r') as f:
                custom_config = json.load(f)
                # Merge with defaults
                default_config.update(custom_config)
        
        return default_config
    
    def save_config(self, filename="rf_collection_config.json"):
        """Save current configuration to file"""
        with open(filename, 'w') as f:
            json.dump(self.config, f, indent=2)
        print(f"Configuration saved to {filename}")
    
    def test_sample_rates(self, device_args=""):
        """Test what sample rates work on this system"""
        print("Testing sample rates to find system capabilities...")
        
        test_rates = [200e3, 300e3, 400e3, 500e3, 750e3, 1e6, 1.5e6, 2e6, 3e6, 5e6]
        working_rates = []
        
        for rate in test_rates:
            print(f"Testing {rate/1e6:.1f} MS/s...", end=" ", flush=True)
            
            try:
                # Test directly with UHD instead of subprocess
                success = self._test_single_rate(rate, device_args)
                
                if success:
                    working_rates.append(rate)
                    print("✓ PASS")
                else:
                    print("✗ Overflows/Failed")
                    # If we get overflows, stop testing higher rates
                    break
                    
            except Exception as e:
                print(f"✗ Error: {e}")
                break
        
        if not working_rates:
            print("No working sample rates found! Check USRP connection.")
            return []
        
        print(f"\nWorking sample rates: {[f'{r/1e6:.1f} MS/s' for r in working_rates]}")
        print(f"Recommended max rate: {max(working_rates)/1e6:.1f} MS/s")
        
        # Update config with working rates
        self.config["capture_settings"]["sample_rates"] = working_rates
        return working_rates
    
    def _test_single_rate(self, sample_rate, device_args="", test_duration=5):
        """Test a single sample rate directly - optimized to match uhd_rx_cfile performance"""
        
        try:
            # Initialize USRP
            usrp = uhd.usrp.MultiUSRP(device_args)
            
            # Configure USRP exactly like uhd_rx_cfile
            usrp.set_rx_rate(sample_rate)
            usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(2.44e9))
            usrp.set_rx_gain(30)
            
            time.sleep(0.1)
            
            # Get actual rate (important for buffer sizing)
            actual_rate = usrp.get_rx_rate()
            
            # Create receive streamer with minimal settings
            st_args = uhd.usrp.StreamArgs("fc32", "sc16")
            rx_streamer = usrp.get_rx_stream(st_args)
            
            # Use smaller, more manageable buffer
            buffer_size = 1024
            recv_buffer = np.zeros((1, buffer_size), dtype=np.complex64)
            
            # Start streaming
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
            stream_cmd.stream_now = True
            rx_streamer.issue_stream_cmd(stream_cmd)
            
            # Collect data with minimal processing
            start_time = time.time()
            overflow_count = 0
            sample_count = 0
            receive_calls = 0
            
            while time.time() - start_time < test_duration:
                metadata = uhd.types.RXMetadata()
                
                # Simple receive call - no fancy timeout handling
                num_rx_samps = rx_streamer.recv(recv_buffer, metadata)
                receive_calls += 1
                
                if metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
                    overflow_count += 1
                elif metadata.error_code == uhd.types.RXMetadataErrorCode.none:
                    sample_count += num_rx_samps
                
                # Early exit if too many overflows
                if overflow_count > 3:
                    break
            
            # Stop streaming
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
            rx_streamer.issue_stream_cmd(stream_cmd)
            
            # Calculate expected samples
            expected_samples = actual_rate * test_duration * 0.8  # Allow 20% margin
            
            # Clean up
            del usrp
            time.sleep(0.2)
            
            # Success criteria: got reasonable amount of data with minimal overflows
            success = (sample_count > expected_samples and overflow_count <= 3)
            
            if not success:
                efficiency = (sample_count / expected_samples * 100) if expected_samples > 0 else 0
                print(f"(efficiency: {efficiency:.0f}%, overflows: {overflow_count})", end=" ")
            
            return success
            
        except Exception as e:
            print(f"Exception: {str(e)[:50]}...", end=" ")
            return False
    
    def collect_frequency_sweep(self, location_name="default", mode="quick_survey"):
        """Collect data across all configured frequencies"""
        
        settings = self.config["collection_modes"][mode]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create output directory
        output_dir = f"rf_dataset_{location_name}_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        collection_summary = {
            "collection_start": timestamp,
            "location": location_name,
            "mode": mode,
            "settings": settings,
            "captures": []
        }
        
        print(f"Starting frequency sweep collection in {output_dir}")
        print(f"Mode: {mode} | Location: {location_name}")
        print(f"Settings: {settings['sample_rate']/1e6:.1f} MS/s, {settings['duration']}s, {settings['gain']} dB")
        
        total_captures = sum(len(freqs) for freqs in self.config["frequencies"].values())
        capture_count = 0
        
        # Sweep through all frequency bands
        for band_name, frequencies in self.config["frequencies"].items():
            print(f"\n=== {band_name.upper()} ===")
            
            for freq_info in frequencies:
                capture_count += 1
                freq_name = freq_info["name"]
                frequency = freq_info["freq"]
                description = freq_info["description"]
                
                print(f"[{capture_count}/{total_captures}] Capturing {freq_name} ({frequency/1e6:.1f} MHz): {description}")
                
                # Generate filename
                filename = os.path.join(output_dir, f"{band_name}_{freq_name}_{timestamp}")
                
                # Record the data
                success = self.record_single_capture(
                    frequency=frequency,
                    sample_rate=settings["sample_rate"],
                    duration=settings["duration"],
                    gain=settings["gain"],
                    filename=filename,
                    compression=self.config["capture_settings"]["compression"]
                )
                
                # Log the capture
                capture_info = {
                    "band": band_name,
                    "name": freq_name,
                    "frequency_hz": frequency,
                    "description": description,
                    "filename": filename,
                    "timestamp": datetime.now().isoformat(),
                    "success": success,
                    "settings": settings
                }
                
                collection_summary["captures"].append(capture_info)
                
                if success:
                    print(f"  ✓ Captured successfully")
                else:
                    print(f"  ✗ Capture failed")
                
                # Brief pause between captures
                time.sleep(2)
        
        # Save collection summary
        summary_file = os.path.join(output_dir, "collection_summary.json")
        with open(summary_file, 'w') as f:
            json.dump(collection_summary, f, indent=2)
        
        print(f"\nCollection complete! Data saved in {output_dir}")
        print(f"Summary saved to {summary_file}")
        
        return output_dir, collection_summary
    
    def record_single_capture(self, frequency, sample_rate, duration, gain, filename, compression="zstd"):
        """Record a single capture using built-in recording functionality"""
        
        try:
            print(f"  Recording {frequency/1e6:.1f} MHz at {sample_rate/1e6:.1f} MS/s for {duration}s...")
            
            # Initialize USRP
            usrp = uhd.usrp.MultiUSRP()
            
            # Configure USRP
            usrp.set_rx_rate(sample_rate)
            usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(frequency))
            usrp.set_rx_gain(gain)
            time.sleep(0.1)
            
            # Get actual values
            actual_rate = usrp.get_rx_rate()
            num_samples = int(duration * actual_rate)
            
            # Create receive streamer
            st_args = uhd.usrp.StreamArgs("fc32", "sc16")
            st_args.args = "recv_frame_size=8192,num_recv_frames=128"
            rx_streamer = usrp.get_rx_stream(st_args)
            
            # Prepare buffer
            recv_buffer = np.zeros((1, 8192), dtype=np.complex64)
            
            # Initialize compression
            if compression == "zstd" and ZSTD_AVAILABLE:
                compressor = zstd.ZstdCompressor(level=self.config["capture_settings"]["compression_level"])
                output_file = open(filename + ".zst", "wb")
                comp_writer = compressor.stream_writer(output_file)
            elif compression == "none":
                output_file = open(filename + ".dat", "wb")
                comp_writer = None
            else:
                # Fallback to no compression
                output_file = open(filename + ".dat", "wb")
                comp_writer = None
            
            # Start streaming
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
            stream_cmd.stream_now = True
            rx_streamer.issue_stream_cmd(stream_cmd)
            
            # Record data
            samples_collected = 0
            overflow_count = 0
            start_time = time.time()
            
            while samples_collected < num_samples:
                metadata = uhd.types.RXMetadata()
                num_rx_samps = rx_streamer.recv(recv_buffer, metadata, 0.1)
                
                if metadata.error_code == uhd.types.RXMetadataErrorCode.timeout:
                    continue
                elif metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
                    overflow_count += 1
                    continue
                elif metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                    print(f"    Error: {metadata.strerror()}")
                    break
                
                # Store samples
                remaining_samples = num_samples - samples_collected
                samples_to_take = min(num_rx_samps, remaining_samples)
                
                data_chunk = recv_buffer[0][:samples_to_take]
                chunk_bytes = data_chunk.tobytes()
                
                if comp_writer:
                    comp_writer.write(chunk_bytes)
                else:
                    output_file.write(chunk_bytes)
                
                samples_collected += samples_to_take
                
                # Progress indicator for long captures
                if duration > 60 and samples_collected % (num_samples // 10) == 0:
                    progress = (samples_collected / num_samples) * 100
                    print(f"    Progress: {progress:.0f}%")
            
            # Stop streaming
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
            rx_streamer.issue_stream_cmd(stream_cmd)
            
            # Close files
            if comp_writer:
                comp_writer.close()
            output_file.close()
            
            # Create metadata file
            actual_freq = usrp.get_rx_freq()
            actual_gain = usrp.get_rx_gain()
            
            meta_filename = filename + ".meta"
            with open(meta_filename, 'w') as f:
                f.write(f"center_frequency_hz={actual_freq}\n")
                f.write(f"sample_rate_hz={actual_rate}\n")
                f.write(f"gain_db={actual_gain}\n")
                f.write(f"duration_seconds={time.time() - start_time:.2f}\n")
                f.write(f"samples={samples_collected}\n")
                f.write(f"overflow_count={overflow_count}\n")
                f.write(f"compression={compression}\n")
                f.write(f"timestamp={datetime.now().isoformat()}\n")
            
            # Clean up
            del usrp
            time.sleep(0.5)
            
            print(f"    ✓ Captured {samples_collected} samples, {overflow_count} overflows")
            return True
            
        except Exception as e:
            print(f"    ✗ Capture failed: {e}")
            return False
    
    def scheduled_collection(self, location_name, duration_hours=24, interval_minutes=60):
        """Run scheduled collection over time"""
        
        print(f"Starting scheduled collection for {duration_hours} hours")
        print(f"Collection every {interval_minutes} minutes")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=duration_hours)
        next_collection = start_time
        
        collection_count = 0
        
        while datetime.now() < end_time:
            if datetime.now() >= next_collection:
                collection_count += 1
                
                # Determine time slot
                current_time = datetime.now().strftime("%H:%M")
                time_slot = "unknown"
                for slot in self.config["scheduling"]["time_slots"]:
                    if slot["start"] <= current_time <= slot["end"]:
                        time_slot = slot["name"]
                        break
                
                print(f"\n--- Scheduled Collection #{collection_count} ---")
                print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({time_slot})")
                
                # Create location name with time info
                timed_location = f"{location_name}_{time_slot}_{collection_count:03d}"
                
                # Collect data
                self.collect_frequency_sweep(timed_location, mode="quick_survey")
                
                # Schedule next collection
                next_collection = datetime.now() + timedelta(minutes=interval_minutes)
                print(f"Next collection at: {next_collection.strftime('%H:%M:%S')}")
            
            # Sleep for a minute before checking again
            time.sleep(60)
        
        print(f"\nScheduled collection completed! Total collections: {collection_count}")
    
    def create_replay_scripts(self, dataset_dir):
        """Create scripts to replay the collected data"""
        
        replay_script = f"""#!/usr/bin/env python3
'''
RF Dataset Replay Script
Generated for dataset: {dataset_dir}
'''

import numpy as np
import uhd
import argparse
import time
import json
import os

def replay_capture(filename, center_freq, sample_rate, gain=30, loop=False):
    '''Replay a single capture file'''
    
    print(f"Loading {{filename}}...")
    
    # Load IQ data (adjust for compression if needed)
    if filename.endswith('.zst'):
        import zstandard as zstd
        with open(filename, 'rb') as f:
            dctx = zstd.ZstdDecompressor()
            decompressed_data = dctx.stream_reader(f).read()
        data = np.frombuffer(decompressed_data, dtype=np.complex64)
    else:
        data = np.fromfile(filename, dtype=np.complex64)
    
    print(f"Loaded {{len(data)}} samples")
    
    # Initialize USRP for transmission
    usrp = uhd.usrp.MultiUSRP()
    usrp.set_tx_rate(sample_rate)
    usrp.set_tx_freq(uhd.libpyuhd.types.tune_request(center_freq))
    usrp.set_tx_gain(gain)
    
    # Create transmit streamer
    st_args = uhd.usrp.StreamArgs("fc32", "sc16")
    tx_streamer = usrp.get_tx_stream(st_args)
    
    print(f"Replaying at {{center_freq/1e6:.1f}} MHz, {{sample_rate/1e6:.1f}} MS/s")
    
    while True:
        # Transmit the data
        metadata = uhd.types.TXMetadata()
        tx_streamer.send(data, metadata)
        
        if not loop:
            break
        
        print("Looping replay...")

def main():
    parser = argparse.ArgumentParser(description='Replay RF dataset captures')
    parser.add_argument('--capture', type=str, help='Specific capture file to replay')
    parser.add_argument('--freq', type=float, help='Center frequency (Hz)')
    parser.add_argument('--rate', type=float, help='Sample rate (Hz)')
    parser.add_argument('--gain', type=float, default=30, help='TX gain (dB)')
    parser.add_argument('--loop', action='store_true', help='Loop the replay')
    
    args = parser.parse_args()
    
    if args.capture and args.freq and args.rate:
        replay_capture(args.capture, args.freq, args.rate, args.gain, args.loop)
    else:
        print("Available captures in this dataset:")
        # List available captures from summary
        summary_file = "collection_summary.json"
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            for capture in summary['captures']:
                if capture['success']:
                    print(f"  {{capture['filename']}} - {{capture['description']}} ({{capture['frequency_hz']/1e6:.1f}} MHz)")

if __name__ == "__main__":
    main()
"""
        
        replay_file = os.path.join(dataset_dir, "replay_dataset.py")
        with open(replay_file, 'w') as f:
            f.write(replay_script)
        
        os.chmod(replay_file, 0o755)
        print(f"Replay script created: {replay_file}")

def main():
    parser = argparse.ArgumentParser(description='RF Environment Dataset Collection System')
    parser.add_argument('--config', type=str, help='Configuration file (JSON)')
    parser.add_argument('--save-config', action='store_true', help='Save default configuration and exit')
    parser.add_argument('--test-rates', action='store_true', help='Test sample rates and update config')
    parser.add_argument('--location', type=str, default='default', help='Location identifier')
    parser.add_argument('--mode', choices=['quick_survey', 'detailed_capture', 'long_term'], 
                       default='quick_survey', help='Collection mode')
    parser.add_argument('--scheduled', action='store_true', help='Run scheduled collection')
    parser.add_argument('--duration', type=float, default=24, help='Scheduled collection duration (hours)')
    parser.add_argument('--interval', type=float, default=60, help='Collection interval (minutes)')
    parser.add_argument('--args', type=str, default="", help='Device arguments for USRP')
    
    args = parser.parse_args()
    
    collector = DatasetCollector(args.config)
    
    if args.save_config:
        collector.save_config()
        return
    
    if args.test_rates:
        collector.test_sample_rates(args.args)
        collector.save_config("updated_config.json")
        return
    
    if args.scheduled:
        collector.scheduled_collection(args.location, args.duration, args.interval)
    else:
        dataset_dir, summary = collector.collect_frequency_sweep(args.location, args.mode)
        collector.create_replay_scripts(dataset_dir)

if __name__ == "__main__":
    main()
