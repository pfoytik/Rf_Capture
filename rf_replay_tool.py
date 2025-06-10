#!/usr/bin/env python3
"""
RF Dataset Replay Tool
Replays captured RF data through USRP for transmission or analysis
"""

import uhd
import numpy as np
import argparse
import time
import json
import os
import sys
import threading
from datetime import datetime

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

class RFReplayer:
    """Handles RF data replay through USRP"""
    
    def __init__(self, device_args=""):
        self.device_args = device_args
        self.usrp = None
        
    def load_iq_data(self, filename):
        """Load I/Q data from various compressed formats"""
        
        print(f"Loading {filename}...")
        
        if filename.endswith('.zst'):
            if not ZSTD_AVAILABLE:
                raise ValueError("zstandard library not installed for .zst files")
            
            with open(filename, 'rb') as f:
                dctx = zstd.ZstdDecompressor()
                decompressed_data = dctx.stream_reader(f).read()
            data = np.frombuffer(decompressed_data, dtype=np.complex64)
            
        elif filename.endswith('.gz'):
            import gzip
            with gzip.open(filename, 'rb') as f:
                data_bytes = f.read()
            data = np.frombuffer(data_bytes, dtype=np.complex64)
            
        elif filename.endswith('.xz'):
            import lzma
            with lzma.open(filename, 'rb') as f:
                data_bytes = f.read()
            data = np.frombuffer(data_bytes, dtype=np.complex64)
            
        elif filename.endswith('.npz'):
            npz_data = np.load(filename)
            data = npz_data['iq_data']
            
        elif filename.endswith('.dat'):
            data = np.fromfile(filename, dtype=np.complex64)
            
        else:
            # Try as raw binary
            data = np.fromfile(filename, dtype=np.complex64)
        
        print(f"Loaded {len(data)} I/Q samples ({len(data)*8/1024/1024:.1f} MB)")
        return data
    
    def load_metadata(self, data_filename):
        """Load metadata from corresponding .meta file"""
        
        # Try to find metadata file
        meta_filename = data_filename + ".meta"
        if not os.path.exists(meta_filename):
            # Try without extension
            base_name = os.path.splitext(data_filename)[0]
            meta_filename = base_name + ".meta"
        
        if os.path.exists(meta_filename):
            metadata = {}
            with open(meta_filename, 'r') as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        key, value = line.strip().split('=', 1)
                        try:
                            # Try to convert to number
                            if '.' in value:
                                metadata[key] = float(value)
                            else:
                                metadata[key] = int(value)
                        except ValueError:
                            metadata[key] = value
            
            print(f"Loaded metadata: {metadata.get('center_frequency_hz', 'Unknown')/1e6:.1f} MHz, "
                  f"{metadata.get('sample_rate_hz', 'Unknown')/1e6:.1f} MS/s")
            return metadata
        else:
            print("No metadata file found - you'll need to specify frequency and sample rate")
            return {}
    
    def replay_data(self, data, center_freq, sample_rate, tx_gain=30, loop=False, 
                   scale_factor=1.0, delay_between_loops=1.0):
        """Replay I/Q data through USRP transmitter"""
        
        print(f"Initializing USRP for transmission...")
        
        # Initialize USRP for transmission
        self.usrp = uhd.usrp.MultiUSRP(self.device_args)
        
        # Configure transmitter
        self.usrp.set_tx_rate(sample_rate)
        self.usrp.set_tx_freq(uhd.libpyuhd.types.tune_request(center_freq))
        self.usrp.set_tx_gain(tx_gain)
        
        # Wait for frequency to settle
        time.sleep(0.1)
        
        # Get actual configured values
        actual_rate = self.usrp.get_tx_rate()
        actual_freq = self.usrp.get_tx_freq()
        actual_gain = self.usrp.get_tx_gain()
        
        print(f"Transmission settings:")
        print(f"  Frequency: {actual_freq/1e6:.3f} MHz")
        print(f"  Sample Rate: {actual_rate/1e6:.3f} MS/s")
        print(f"  TX Gain: {actual_gain:.1f} dB")
        print(f"  Scale Factor: {scale_factor}")
        print(f"  Loop Mode: {'Yes' if loop else 'No'}")
        
        # Scale the data if requested
        if scale_factor != 1.0:
            data = data * scale_factor
            print(f"Scaled signal amplitude by {scale_factor}")
        
        # Create transmit streamer
        st_args = uhd.usrp.StreamArgs("fc32", "sc16")
        tx_streamer = self.usrp.get_tx_stream(st_args)
        
        # Calculate transmission duration
        duration = len(data) / actual_rate
        print(f"Data duration: {duration:.2f} seconds")
        
        loop_count = 0
        
        try:
            while True:
                loop_count += 1
                if loop:
                    print(f"Starting transmission loop #{loop_count}...")
                else:
                    print("Starting transmission...")
                
                # Transmit the data
                metadata = uhd.types.TXMetadata()
                metadata.start_of_burst = True
                metadata.end_of_burst = True
                
                # Send data in chunks if it's large
                chunk_size = 10000
                samples_sent = 0
                
                start_time = time.time()
                
                for i in range(0, len(data), chunk_size):
                    chunk = data[i:i+chunk_size]
                    
                    # Set metadata for first and last chunks
                    if i == 0:
                        metadata.start_of_burst = True
                    else:
                        metadata.start_of_burst = False
                        
                    if i + chunk_size >= len(data):
                        metadata.end_of_burst = True
                    else:
                        metadata.end_of_burst = False
                    
                    tx_streamer.send(chunk, metadata)
                    samples_sent += len(chunk)
                    
                    # Progress indicator for long transmissions
                    if duration > 10 and samples_sent % (len(data) // 10) == 0:
                        progress = (samples_sent / len(data)) * 100
                        print(f"  Progress: {progress:.0f}%")
                
                elapsed = time.time() - start_time
                print(f"Transmission complete in {elapsed:.2f} seconds")
                
                if not loop:
                    break
                
                if delay_between_loops > 0:
                    print(f"Waiting {delay_between_loops} seconds before next loop...")
                    time.sleep(delay_between_loops)
                
        except KeyboardInterrupt:
            print(f"\nTransmission stopped by user after {loop_count} loops")
        
        print("Replay complete!")
    
    def analyze_data(self, data, sample_rate):
        """Provide basic analysis of the I/Q data"""
        
        print(f"\n=== Data Analysis ===")
        print(f"Samples: {len(data)}")
        print(f"Duration: {len(data)/sample_rate:.2f} seconds")
        print(f"Sample Rate: {sample_rate/1e6:.3f} MS/s")
        
        # Power statistics
        power = np.abs(data)**2
        avg_power = np.mean(power)
        max_power = np.max(power)
        power_std = np.std(power)
        
        print(f"Average Power: {10*np.log10(avg_power + 1e-12):.1f} dB")
        print(f"Peak Power: {10*np.log10(max_power + 1e-12):.1f} dB")
        print(f"Power Std Dev: {10*np.log10(power_std + 1e-12):.1f} dB")
        
        # Dynamic range
        dynamic_range = 10*np.log10(max_power/avg_power) if avg_power > 0 else 0
        print(f"Dynamic Range: {dynamic_range:.1f} dB")
        
        # Frequency domain analysis
        if len(data) >= 1024:
            fft_data = np.fft.fftshift(np.fft.fft(data[:1024]))
            fft_power = np.abs(fft_data)**2
            peak_bin = np.argmax(fft_power)
            freq_bins = np.fft.fftshift(np.fft.fftfreq(1024, 1/sample_rate))
            peak_offset = freq_bins[peak_bin]
            
            print(f"Peak Frequency Offset: {peak_offset/1e3:.1f} kHz from center")
        
        return {
            'samples': len(data),
            'duration': len(data)/sample_rate,
            'avg_power_db': 10*np.log10(avg_power + 1e-12),
            'peak_power_db': 10*np.log10(max_power + 1e-12),
            'dynamic_range_db': dynamic_range
        }
    
    def list_dataset_captures(self, dataset_dir):
        """List available captures in a dataset directory"""
        
        summary_file = os.path.join(dataset_dir, "collection_summary.json")
        
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                summary = json.load(f)
            
            print(f"Dataset: {dataset_dir}")
            print(f"Location: {summary.get('location', 'Unknown')}")
            print(f"Collection Date: {summary.get('collection_start', 'Unknown')}")
            print(f"Mode: {summary.get('mode', 'Unknown')}")
            print(f"\nAvailable captures:")
            
            for i, capture in enumerate(summary.get('captures', [])):
                if capture.get('success', False):
                    filename = capture['filename']
                    # Find the actual file (might have compression extension)
                    actual_file = None
                    for ext in ['.zst', '.gz', '.xz', '.dat']:
                        if os.path.exists(filename + ext):
                            actual_file = filename + ext
                            break
                    
                    if actual_file:
                        file_size = os.path.getsize(actual_file) / 1024 / 1024
                        print(f"  [{i+1:2d}] {capture['name']:10s} - {capture['description']:25s}")
                        print(f"       {capture['frequency_hz']/1e6:7.1f} MHz - {actual_file} ({file_size:.1f} MB)")
            
            return summary
        else:
            print(f"No collection summary found in {dataset_dir}")
            print("Available files:")
            for file in os.listdir(dataset_dir):
                if file.endswith(('.zst', '.gz', '.xz', '.dat', '.npz')):
                    file_size = os.path.getsize(os.path.join(dataset_dir, file)) / 1024 / 1024
                    print(f"  {file} ({file_size:.1f} MB)")
            return None

def main():
    parser = argparse.ArgumentParser(description='RF Dataset Replay Tool')
    parser.add_argument('--file', type=str, help='RF data file to replay')
    parser.add_argument('--dataset', type=str, help='Dataset directory to explore')
    parser.add_argument('--freq', type=float, help='Center frequency (Hz)')
    parser.add_argument('--rate', type=float, help='Sample rate (Hz)')
    parser.add_argument('--gain', type=float, default=30, help='TX gain (dB)')
    parser.add_argument('--scale', type=float, default=1.0, help='Signal scale factor')
    parser.add_argument('--loop', action='store_true', help='Loop the replay continuously')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between loops (seconds)')
    parser.add_argument('--analyze-only', action='store_true', help='Only analyze data, don\'t transmit')
    parser.add_argument('--list-only', action='store_true', help='Only list available captures')
    parser.add_argument('--args', type=str, default="", help='Device arguments for USRP')
    
    args = parser.parse_args()
    
    replayer = RFReplayer(args.args)
    
    # List dataset contents
    if args.dataset:
        summary = replayer.list_dataset_captures(args.dataset)
        
        if args.list_only:
            return
        
        if not args.file:
            print("\nUse --file to specify which capture to replay")
            return
        
        # If file doesn't include path, assume it's in the dataset directory
        if not os.path.dirname(args.file):
            args.file = os.path.join(args.dataset, args.file)
    
    if not args.file:
        print("Please specify --file or --dataset")
        return
    
    if not os.path.exists(args.file):
        print(f"File not found: {args.file}")
        return
    
    # Load the data
    try:
        data = replayer.load_iq_data(args.file)
        metadata = replayer.load_metadata(args.file)
        
        # Get frequency and sample rate
        center_freq = args.freq or metadata.get('center_frequency_hz')
        sample_rate = args.rate or metadata.get('sample_rate_hz')
        
        if not center_freq or not sample_rate:
            print("Missing frequency or sample rate information!")
            print("Specify with --freq and --rate, or ensure .meta file exists")
            return
        
        # Analyze the data
        analysis = replayer.analyze_data(data, sample_rate)
        
        if args.analyze_only:
            return
        
        # Replay the data
        replayer.replay_data(
            data, center_freq, sample_rate, 
            args.gain, args.loop, args.scale, args.delay
        )
        
    except Exception as e:
        print(f"Error: {e}")
        return

if __name__ == "__main__":
    main()
