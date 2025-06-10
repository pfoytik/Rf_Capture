#!/usr/bin/env python3
"""
Parallel RF Recording Script for USRP B205
Uses separate threads for data acquisition, compression, and disk I/O
"""

import uhd
import numpy as np
import argparse
import time
import sys
import gzip
import lzma
import threading
import queue
import multiprocessing
import subprocess
import signal
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False

class ParallelCompressor:
    """Handles parallel compression with separate threads for compression and I/O"""
    
    def __init__(self, filename, compression='none', compression_level=3, num_threads=None):
        self.filename = filename
        self.compression = compression
        self.compression_level = compression_level
        self.samples_written = 0
        self.bytes_written = 0
        self.running = True
        
        # Use number of CPU cores for compression threads
        if num_threads is None:
            num_threads = max(1, multiprocessing.cpu_count() - 1)
        self.num_threads = num_threads
        
        # Queues for pipeline: raw_data -> compressed_data -> disk_write
        self.raw_queue = queue.Queue(maxsize=10)
        self.compressed_queue = queue.Queue(maxsize=20)
        
        # File handle
        if compression == 'none':
            self.file_handle = open(filename, 'wb')
        elif compression == 'gzip':
            self.file_handle = open(filename + '.gz', 'wb')
        elif compression == 'lzma':
            self.file_handle = open(filename + '.xz', 'wb')
        elif compression == 'zstd':
            if not ZSTD_AVAILABLE:
                raise ValueError("zstandard library not installed")
            self.file_handle = open(filename + '.zst', 'wb')
        else:
            raise ValueError(f"Unsupported compression method: {compression}")
        
        # Start worker threads
        self.executor = ThreadPoolExecutor(max_workers=num_threads)
        self.io_thread = threading.Thread(target=self._io_worker, daemon=True)
        self.io_thread.start()
        
        print(f"Started parallel compressor with {num_threads} compression threads")
    
    def write_chunk(self, data_chunk):
        """Queue data chunk for parallel compression"""
        try:
            self.raw_queue.put_nowait((data_chunk.copy(), len(data_chunk)))
            self.samples_written += len(data_chunk)
        except queue.Full:
            print("Warning: Compression queue full, may cause overflows")
    
    def _compress_chunk(self, data_and_size):
        """Compress a single chunk (runs in thread pool)"""
        data_chunk, chunk_size = data_and_size
        
        if self.compression == 'none':
            return data_chunk.tobytes()
        elif self.compression == 'gzip':
            return gzip.compress(data_chunk.tobytes(), compresslevel=self.compression_level)
        elif self.compression == 'lzma':
            return lzma.compress(data_chunk.tobytes(), preset=self.compression_level)
        elif self.compression == 'zstd':
            compressor = zstd.ZstdCompressor(level=self.compression_level)
            return compressor.compress(data_chunk.tobytes())
    
    def _io_worker(self):
        """I/O worker thread - writes compressed data to disk"""
        while self.running:
            try:
                # Get raw data
                raw_data = self.raw_queue.get(timeout=0.1)
                
                # Submit compression job
                future = self.executor.submit(self._compress_chunk, raw_data)
                
                # Queue the future result for writing
                self.compressed_queue.put(future)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Compression error: {e}")
        
        # Write remaining compressed data
        while not self.compressed_queue.empty():
            try:
                future = self.compressed_queue.get_nowait()
                compressed_data = future.result()
                self.file_handle.write(compressed_data)
                self.bytes_written += len(compressed_data)
            except:
                break
    
    def _write_compressed_data(self):
        """Write compressed data from queue to disk"""
        while self.running or not self.compressed_queue.empty():
            try:
                future = self.compressed_queue.get(timeout=0.1)
                compressed_data = future.result()  # Get result from compression thread
                self.file_handle.write(compressed_data)
                self.bytes_written += len(compressed_data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"I/O error: {e}")
    
    def close(self):
        """Close the compressor and return final stats"""
        self.running = False
        
        # Process remaining raw data
        while not self.raw_queue.empty():
            try:
                raw_data = self.raw_queue.get_nowait()
                future = self.executor.submit(self._compress_chunk, raw_data)
                compressed_data = future.result()
                self.file_handle.write(compressed_data)
                self.bytes_written += len(compressed_data)
            except:
                break
        
        # Process remaining compressed data
        while not self.compressed_queue.empty():
            try:
                future = self.compressed_queue.get_nowait()
                compressed_data = future.result()
                self.file_handle.write(compressed_data)
                self.bytes_written += len(compressed_data)
            except:
                break
        
        # Shutdown threads
        self.executor.shutdown(wait=True)
        if self.io_thread.is_alive():
            self.io_thread.join(timeout=5)
        
        self.file_handle.close()
        
        # Get actual file size
        extensions = {'gzip': '.gz', 'lzma': '.xz', 'zstd': '.zst', 'none': ''}
        compressed_filename = self.filename + extensions.get(self.compression, '')
        actual_file_size = os.path.getsize(compressed_filename) if os.path.exists(compressed_filename) else self.bytes_written
        
        return self.samples_written, actual_file_size

class UHDFFTVisualization:
    """Manages UHD FFT visualization in a separate process"""
    
    def __init__(self, frequency, sample_rate, gain, device_args="", fft_size=1024, update_rate=5):
        self.frequency = frequency
        self.sample_rate = sample_rate
        self.gain = gain
        self.device_args = device_args
        self.fft_size = fft_size
        self.update_rate = update_rate
        self.process = None
        self.running = False
    
    def start(self):
        """Start the UHD FFT visualization"""
        try:
            cmd = [
                'uhd_fft',
                '-f', str(self.frequency),
                '-s', str(self.sample_rate),
                '-g', str(self.gain),
                '--fft-size', str(self.fft_size),
                '--update-rate', str(self.update_rate)
            ]
            
            if self.device_args:
                cmd.extend(['--args', self.device_args])
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid
            )
            
            time.sleep(1)
            
            if self.process.poll() is None:
                self.running = True
                print("UHD FFT visualization started successfully!")
                return True
            else:
                stderr_output = self.process.stderr.read().decode()
                print(f"UHD FFT failed to start: {stderr_output}")
                return False
            
        except Exception as e:
            print(f"Failed to start UHD FFT: {e}")
            return False
    
    def is_running(self):
        """Check if the visualization is still running"""
        if not self.process:
            return False
        
        poll_result = self.process.poll()
        if poll_result is not None:
            self.running = False
            return False
        
        return self.running
    
    def stop(self):
        """Stop the UHD FFT visualization"""
        if self.process and self.running:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                    self.process.wait()
                print("UHD FFT visualization stopped")
            except Exception as e:
                print(f"Error stopping UHD FFT: {e}")
            finally:
                self.running = False
                self.process = None

def record_rf_parallel(frequency, sample_rate, duration, filename, 
                      gain=30, compression='none', compression_level=3, chunk_size=1024*1024,
                      enable_viz=True, device_args="", recv_timeout=0.1, num_threads=None):
    """
    Record RF data with parallel compression
    """
    
    # Display CPU info
    cpu_count = multiprocessing.cpu_count()
    threads_used = num_threads if num_threads else max(1, cpu_count - 1)
    
    print(f"Starting parallel RF recording...")
    print(f"CPU cores: {cpu_count}, Using {threads_used} compression threads")
    print(f"Frequency: {frequency/1e6:.2f} MHz")
    print(f"Sample Rate: {sample_rate/1e6:.2f} MS/s")
    print(f"Duration: {duration} seconds")
    print(f"Gain: {gain} dB")
    print(f"Compression: {compression}" + (f" (level {compression_level})" if compression != 'none' else ""))
    print(f"UHD FFT Visualization: {'Enabled' if enable_viz else 'Disabled'}")
    print(f"Output file: {filename}")
    
    # Test USRP connectivity
    print("\nTesting USRP connectivity...")
    try:
        test_usrp = uhd.usrp.MultiUSRP(device_args)
        print("✓ USRP connection successful")
        del test_usrp
        time.sleep(0.5)
    except Exception as e:
        print(f"✗ USRP connection failed: {e}")
        return
    
    # Start UHD FFT visualization if requested
    uhd_fft = None
    if enable_viz:
        print("\nStarting UHD FFT visualization...")
        uhd_fft = UHDFFTVisualization(frequency, sample_rate, gain, device_args, fft_size=1024, update_rate=5)
        if uhd_fft.start():
            print("Waiting 5 seconds for UHD FFT to fully initialize...")
            time.sleep(5)
            
            if not uhd_fft.is_running():
                print("UHD FFT process died. Continuing without visualization.")
                uhd_fft = None
        else:
            print("Failed to start UHD FFT. Continuing without visualization.")
            uhd_fft = None
    
    # Create USRP object for recording
    print("Initializing USRP for recording...")
    try:
        usrp = uhd.usrp.MultiUSRP(device_args)
        print("✓ USRP initialized for recording")
    except Exception as e:
        print(f"✗ Failed to initialize USRP for recording: {e}")
        if uhd_fft:
            print("Stopping UHD FFT and retrying...")
            uhd_fft.stop()
            time.sleep(2)
            try:
                usrp = uhd.usrp.MultiUSRP(device_args)
                print("✓ USRP initialized after stopping visualization")
                uhd_fft = None
            except Exception as e2:
                print(f"✗ Still failed to initialize USRP: {e2}")
                return
        else:
            return
    
    # Configure USRP
    usrp.set_rx_rate(sample_rate)
    usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(frequency))
    usrp.set_rx_gain(gain)
    time.sleep(0.1)
    
    # Get actual configured values
    actual_rate = usrp.get_rx_rate()
    actual_freq = usrp.get_rx_freq()
    actual_gain = usrp.get_rx_gain()
    
    print(f"\nActual recording values:")
    print(f"Sample Rate: {actual_rate/1e6:.2f} MS/s")
    print(f"Frequency: {actual_freq/1e6:.2f} MHz")
    print(f"Gain: {actual_gain:.1f} dB")
    
    # Calculate number of samples
    num_samples = int(duration * actual_rate)
    
    # Create receive streamer with optimized args
    st_args = uhd.usrp.StreamArgs("fc32", "sc16")
    st_args.args = "recv_frame_size=8192,num_recv_frames=128"
    rx_streamer = usrp.get_rx_stream(st_args)
    
    # Prepare larger buffer
    buffer_size = 8192
    recv_buffer = np.zeros((1, buffer_size), dtype=np.complex64)
    
    # Initialize parallel compressor
    compressor = ParallelCompressor(filename, compression, compression_level, num_threads)
    
    # Start streaming
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    stream_cmd.stream_now = True
    rx_streamer.issue_stream_cmd(stream_cmd)
    
    # Record data with parallel compression
    samples_collected = 0
    chunk_buffer = []
    chunk_samples = 0
    overflow_count = 0
    
    print(f"\nRecording {num_samples} samples with parallel compression...")
    print("Press Ctrl+C to stop early, or close the FFT window")
    start_time = time.time()
    
    try:
        while samples_collected < num_samples:
            # Check if UHD FFT window was closed
            if uhd_fft and not uhd_fft.is_running():
                print("\nUHD FFT window closed. Stopping recording...")
                break
            
            # Receive samples with timeout
            metadata = uhd.types.RXMetadata()
            num_rx_samps = rx_streamer.recv(recv_buffer, metadata, recv_timeout)
            
            if metadata.error_code == uhd.types.RXMetadataErrorCode.timeout:
                continue
            elif metadata.error_code == uhd.types.RXMetadataErrorCode.overflow:
                overflow_count += 1
                if overflow_count % 100 == 1:
                    print("O", end="", flush=True)
                continue
            elif metadata.error_code != uhd.types.RXMetadataErrorCode.none:
                print(f"\nReceiver error: {metadata.strerror()}")
                continue
            
            # Store samples in chunk buffer
            remaining_samples = num_samples - samples_collected
            samples_to_take = min(num_rx_samps, remaining_samples)
            
            chunk_buffer.append(recv_buffer[0][:samples_to_take].copy())
            chunk_samples += samples_to_take
            samples_collected += samples_to_take
            
            # Write chunk when buffer is full
            if chunk_samples >= chunk_size:
                chunk_data = np.concatenate(chunk_buffer)
                compressor.write_chunk(chunk_data)
                
                # Reset chunk buffer
                chunk_buffer = []
                chunk_samples = 0
            
            # Progress indicator
            if samples_collected % (num_samples // 20) == 0:
                progress = (samples_collected / num_samples) * 100
                ram_usage = chunk_samples * 8 / 1024 / 1024
                elapsed = time.time() - start_time
                rate_mbps = (samples_collected * 8 / 1024 / 1024) / elapsed if elapsed > 0 else 0
                print(f"\nProgress: {progress:.1f}% | RAM: {ram_usage:.1f}MB | Rate: {rate_mbps:.1f}MB/s | Overflows: {overflow_count}")
    
    except KeyboardInterrupt:
        print("\nRecording interrupted by user")
    
    finally:
        # Stop streaming
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        rx_streamer.issue_stream_cmd(stream_cmd)
        
        # Write any remaining data in buffer
        if chunk_buffer:
            chunk_data = np.concatenate(chunk_buffer)
            compressor.write_chunk(chunk_data)
        
        # Stop UHD FFT visualization
        if uhd_fft:
            uhd_fft.stop()
        
        # Close compressor and get final stats
        print("\nFinalizing compression and file I/O...")
        final_samples, final_bytes = compressor.close()
    
    recording_time = time.time() - start_time
    original_size = samples_collected * 8
    
    # Create metadata file
    meta_filename = filename + ".meta"
    with open(meta_filename, 'w') as f:
        f.write(f"# RF Recording Metadata\n")
        f.write(f"# Generated: {datetime.now()}\n")
        f.write(f"center_frequency_hz={actual_freq}\n")
        f.write(f"sample_rate_hz={actual_rate}\n")
        f.write(f"gain_db={actual_gain}\n")
        f.write(f"duration_seconds={recording_time:.2f}\n")
        f.write(f"samples={samples_collected}\n")
        f.write(f"data_type=complex64\n")
        f.write(f"compression={compression}\n")
        f.write(f"compression_threads={threads_used}\n")
        f.write(f"visualization=uhd_fft\n")
        f.write(f"overflow_count={overflow_count}\n")
        f.write(f"original_size_bytes={original_size}\n")
        f.write(f"compressed_size_bytes={final_bytes}\n")
        f.write(f"compression_ratio={original_size/final_bytes:.2f}\n")
    
    print(f"\nRecording complete!")
    print(f"Samples recorded: {samples_collected}")
    print(f"Duration: {recording_time:.2f} seconds")
    print(f"Compression threads used: {threads_used}")
    print(f"Overflow count: {overflow_count}")
    print(f"Original size: {original_size/1024/1024:.1f} MB")
    print(f"Compressed size: {final_bytes/1024/1024:.1f} MB")
    print(f"Compression ratio: {original_size/final_bytes:.2f}:1")
    print(f"Average data rate: {(final_bytes/1024/1024)/recording_time:.1f} MB/s")
    print(f"Metadata saved to {meta_filename}")

def main():
    parser = argparse.ArgumentParser(description='Record RF data with parallel compression')
    parser.add_argument('-f', '--frequency', type=float, required=True,
                       help='Center frequency in Hz (e.g., 2.44e9 for 2.44 GHz)')
    parser.add_argument('-s', '--sample-rate', type=float, required=True,
                       help='Sample rate in Hz (e.g., 10e6 for 10 MS/s)')
    parser.add_argument('-t', '--time', type=float, required=True,
                       help='Recording duration in seconds')
    parser.add_argument('-o', '--output', type=str, required=True,
                       help='Output filename')
    parser.add_argument('-g', '--gain', type=float, default=30,
                       help='RF gain in dB (default: 30)')
    parser.add_argument('-c', '--compression', choices=['none', 'gzip', 'lzma', 'zstd'],
                       default='none', help='Compression method (default: none)')
    parser.add_argument('--compression-level', type=int, default=3,
                       help='Compression level (default: 3)')
    parser.add_argument('--chunk-size', type=int, default=1024*1024,
                       help='Samples per chunk (default: 1M samples)')
    parser.add_argument('--no-viz', action='store_true',
                       help='Disable UHD FFT visualization')
    parser.add_argument('--viz-only', action='store_true',
                       help='Only run visualization without recording')
    parser.add_argument('--args', type=str, default="",
                       help='Device arguments for USRP (e.g., serial=12345)')
    parser.add_argument('--timeout', type=float, default=0.1,
                       help='Receive timeout in seconds (default: 0.1)')
    parser.add_argument('--threads', type=int, default=None,
                       help='Number of compression threads (default: auto)')
    
    args = parser.parse_args()
    
    # Check zstd availability if requested
    if args.compression == 'zstd' and not ZSTD_AVAILABLE:
        print("Error: zstandard library not installed.")
        print("Install with: pip install zstandard")
        sys.exit(1)
    
    # Handle visualization-only mode
    if args.viz_only:
        print("Running visualization only mode...")
        try:
            subprocess.run([
                'uhd_fft',
                '-f', str(args.frequency),
                '-s', str(args.sample_rate),
                '-g', str(args.gain),
                '--args', args.args
            ])
        except KeyboardInterrupt:
            print("\nVisualization stopped")
        sys.exit(0)
    
    try:
        record_rf_parallel(
            args.frequency, args.sample_rate, args.time, 
            args.output, args.gain, args.compression, args.compression_level,
            args.chunk_size, not args.no_viz, args.args, args.timeout, args.threads
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
