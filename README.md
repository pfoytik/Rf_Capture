# RF Environment Dataset Collection and Replay Toolkit

A comprehensive toolkit for capturing, analyzing, and replaying RF environments using USRP B205 SDRs. This toolkit enables systematic collection of RF datasets for research, testing, and signal analysis.

## Table of Contents
- [Quick Start for Non-Technical Users](#quick-start-for-non-technical-users)
- [Hardware Requirements](#hardware-requirements)
- [Software Setup](#software-setup)
- [Detailed Usage](#detailed-usage)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [Legal and Safety Considerations](#legal-and-safety-considerations)

## Quick Start for Non-Technical Users

*This section assumes all software is already installed and the USRP is connected.*

### What This Toolkit Does

This toolkit captures invisible radio signals (like WiFi, cell phone towers, FM radio) from the air around you and saves them as data files. Later, you can replay these signals or analyze them to understand the "radio environment" of different locations.

Think of it like recording audio, but instead of recording sound waves, you're recording radio waves.

### Step 1: Test Your Setup

First, let's make sure everything is working:

1. **Open a terminal** (the black command window)
2. **Type this command** and press Enter:
   ```bash
   python3 rf_dataset_collector.py --test-rates
   ```
3. **Wait for it to finish** (takes 1-2 minutes)
4. **Look for the result** - it should say something like "Recommended max rate: 5.0 MS/s"

✅ **If you see a recommended rate**: Great! Your system is working.  
❌ **If you see errors**: Ask your technical person to check the setup.

### Step 2: Capture Your First Dataset

Now let's capture radio signals from your location:

1. **Choose a location name** (use underscores instead of spaces):
   - Good examples: `my_office`, `coffee_shop`, `home_evening`
   - Avoid: `my office`, `café`, `room #5`

2. **Run this command** (replace `my_office` with your location name):
   ```bash
   python3 rf_dataset_collector.py --location "my_office" --mode quick_survey
   ```

3. **Wait for it to complete** (takes about 15 minutes)
   - You'll see progress like: `[1/10] Capturing ch1 (2412.0 MHz): WiFi Channel 1`
   - Each step captures signals from a different frequency

4. **When finished**, you'll see: `Collection complete! Data saved in rf_dataset_my_office_YYYYMMDD_HHMMSS`

### Step 3: Look at Your Data

Let's see what you captured:

1. **List your data** (replace the folder name with yours):
   ```bash
   python3 rf_replay_tool.py --dataset rf_dataset_my_office_* --list-only
   ```

2. **You'll see a list** of captured signals like:
   ```
   [ 1] ch1        - WiFi Channel 1        2412.0 MHz - wifi_2_4_ghz_ch1_*.zst (45.2 MB)
   [ 2] ch6        - WiFi Channel 6        2437.0 MHz - wifi_2_4_ghz_ch6_*.zst (52.1 MB)
   [ 3] fm_radio   - FM Radio              100.1 MHz  - other_bands_fm_radio_*.zst (12.3 MB)
   ```

### Step 4: Analyze Your Signals

Let's check how strong the signals were:

1. **Pick one file to analyze** (like WiFi Channel 6):
   ```bash
   python3 rf_replay_tool.py --dataset rf_dataset_my_office_* --file wifi_2_4_ghz_ch6_20250605_104949.zst --analyze-only
   ```

2. **Look at the power level**:
   - **-20 to -40 dB**: Very strong signals (great!)
   - **-40 to -50 dB**: Good signals  
   - **-50 to -60 dB**: Weak signals (okay)
   - **Below -60 dB**: Mostly noise (try again closer to WiFi router)

### Different Collection Types

You can collect different amounts of data:

#### Quick Survey (15 minutes)
```bash
python3 rf_dataset_collector.py --location "location_name" --mode quick_survey
```
- **Time**: 1 minute per frequency (15 minutes total)
- **Use for**: Quick check of radio environment

#### Detailed Capture (1 hour)  
```bash
python3 rf_dataset_collector.py --location "location_name" --mode detailed_capture
```
- **Time**: 5 minutes per frequency (1 hour total)
- **Use for**: High-quality data for analysis

#### Long-term Monitoring (6 hours)
```bash
python3 rf_dataset_collector.py --location "location_name" --mode long_term
```
- **Time**: 30 minutes per frequency (6 hours total)
- **Use for**: Extended monitoring periods

### Collecting from Different Locations

Capture the radio environment from various places:

```bash
# At home
python3 rf_dataset_collector.py --location "home_morning" --mode quick_survey

# At work
python3 rf_dataset_collector.py --location "office_busy" --mode quick_survey

# At a coffee shop
python3 rf_dataset_collector.py --location "starbucks_downtown" --mode quick_survey

# Different times
python3 rf_dataset_collector.py --location "home_evening" --mode quick_survey
```

### Automated Collection Over Time

To collect data automatically every hour for a day:

```bash
python3 rf_dataset_collector.py --location "office" --scheduled --duration 24 --interval 60
```

- **duration 24**: Run for 24 hours
- **interval 60**: Collect data every 60 minutes
- **This will run by itself** - check back later

### Understanding Your Results

After collection, you'll have folders like:
```
rf_dataset_my_office_20241205_143022/
├── wifi_2_4_ghz_ch1_*.zst     ← WiFi signals from channel 1
├── wifi_2_4_ghz_ch6_*.zst     ← WiFi signals from channel 6  
├── wifi_5_ghz_ch36_*.zst      ← 5GHz WiFi signals
├── other_bands_fm_radio_*.zst ← FM radio signals
└── collection_summary.json    ← Information about the collection
```

**File sizes tell you about signal activity:**
- **Large files (50+ MB)**: Lots of radio activity
- **Medium files (10-50 MB)**: Moderate activity  
- **Small files (< 10 MB)**: Quiet radio environment

### Tips for Good Data Collection

1. **For WiFi signals**: Collect near your WiFi router or in busy areas
2. **For quiet environments**: Collect in rural areas or shielded rooms
3. **For comparison**: Collect same location at different times (morning vs evening)
4. **For movement studies**: Collect while walking through building with laptop
5. **Use descriptive names**: `coffee_shop_rush_hour` vs `coffee_shop_empty`

### What to Do if Something Goes Wrong

**If you see "overflow" or lots of 'O' characters:**
- Your computer can't keep up
- Try: `python3 rf_dataset_collector.py --test-rates` to find a working speed

**If you see "No devices found":**
- The USRP isn't connected properly
- Ask your technical person to check connections

**If files are very small (< 5 MB):**
- You're in a quiet radio area, or
- The antenna isn't connected properly
- Try collecting closer to a WiFi router

**If the program stops with errors:**
- Write down the error message
- Ask your technical person for help

### What NOT to Do

❌ **Don't unplug the USRP** while the program is running  
❌ **Don't use spaces in location names** (use underscores: `my_office`)  
❌ **Don't run multiple collections at the same time**  
❌ **Don't worry about the technical details** - just follow the commands  

### Next Steps

Once you have collected data:
- **Compare different locations** by looking at file sizes and power levels
- **Look for patterns** - are some frequencies always busy?
- **Share data** with your technical team for deeper analysis
- **Collect more data** from interesting locations or times

Remember: You're creating a library of "radio fingerprints" from different places and times!

## Hardware Requirements

### Required
- **USRP B205Mini** (or B200/B205) 
- **USB 3.0 port** (USB 2.0 will severely limit performance)
- **Appropriate antennas** for target frequencies
- **RF cables** (SMA connectors)

### Optional for Replay Testing
- **Second USRP B205** for receive-only monitoring
- **RF attenuators** (20-30 dB recommended for safety)
- **50-ohm dummy load** for safe transmission testing
- **RF shielded enclosure** for controlled testing

### System Requirements
- **Ubuntu 20.04+** (other Linux distributions may work)
- **4+ GB RAM** (8+ GB recommended)
- **Fast SSD storage** (captures generate large files)
- **Multi-core CPU** (parallel compression benefits from 4+ cores)

## Software Setup

### 1. Install UHD and Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade

# Install UHD and GNU Radio
sudo apt install uhd-host uhd-tools gnuradio gr-uhd

# Install Python dependencies
sudo apt install python3-uhd python3-numpy python3-matplotlib

# Install compression libraries
pip install zstandard
sudo apt install python3-zstandard

# Download USRP firmware images
sudo uhd_images_downloader
```

### 2. Configure USB Permissions

```bash
# Add USRP udev rules
sudo cp /usr/lib/uhd/utils/uhd-usrp.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add user to USRP group
sudo usermod -a -G usrp $USER

# Log out and back in for group changes to take effect
```

### 3. Verify USRP Connection

```bash
# Find connected USRPs
uhd_find_devices

# Test USRP functionality  
uhd_usrp_probe

# Test basic reception (should show no 'O' overflow characters)
uhd_rx_cfile -f 100e6 -r 1e6 -g 30 --duration 5 /tmp/test.dat
```

### 4. Optimize System Performance

```bash
# Set CPU to performance mode
sudo cpupower frequency-set -g performance

# Increase USB buffer sizes
echo 256 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb

# Disable USB autosuspend
echo -1 | sudo tee /sys/module/usbcore/parameters/autosuspend
```

## Quick Start

### 1. Test Your System Capabilities

```bash
# Find maximum sample rate your system can handle
python3 rf_dataset_collector.py --test-rates
```

### 2. Collect Your First Dataset

```bash
# Quick 1-minute samples across all frequency bands
python3 rf_dataset_collector.py --location "my_office" --mode quick_survey

# Detailed 5-minute samples (uses maximum sample rate)
python3 rf_dataset_collector.py --location "coffee_shop" --mode detailed_capture
```

### 3. Examine Your Data

```bash
# List what was captured
python3 rf_replay_tool.py --dataset rf_dataset_my_office_* --list-only

# Analyze a specific capture
python3 rf_replay_tool.py --dataset rf_dataset_my_office_* --file wifi_2_4_ghz_ch6_*.zst --analyze-only
```

### 4. Test Replay (Safe Method)

```bash
# Connect TX of one USRP to RX of another with attenuator
# Start receiver visualization
uhd_fft -f 2.44e9 -s 5e6 -g 30

# In another terminal, replay your data
python3 rf_replay_tool.py --file rf_dataset_*/wifi_2_4_ghz_ch6_*.zst --gain 10
```

## Detailed Usage

### Dataset Collector (`rf_dataset_collector.py`)

#### Basic Collection Modes

```bash
# Quick survey: 1-minute captures at moderate sample rate
python3 rf_dataset_collector.py --location "home_evening" --mode quick_survey

# Detailed capture: 5-minute captures at maximum sample rate  
python3 rf_dataset_collector.py --location "office_busy" --mode detailed_capture

# Long-term: 30-minute captures for extended analysis
python3 rf_dataset_collector.py --location "apartment_night" --mode long_term
```

#### Scheduled Collection

```bash
# Collect data every hour for 24 hours
python3 rf_dataset_collector.py --location "campus" --scheduled --duration 24 --interval 60

# Collect every 30 minutes for 8 hours  
python3 rf_dataset_collector.py --location "office" --scheduled --duration 8 --interval 30
```

#### Advanced Options

```bash
# Use specific USRP device
python3 rf_dataset_collector.py --location "lab" --args "serial=12345"

# Save and customize configuration
python3 rf_dataset_collector.py --save-config
# Edit rf_collection_config.json, then:
python3 rf_dataset_collector.py --config rf_collection_config.json --location "custom"

# Test only (no data collection)  
python3 rf_dataset_collector.py --test-rates
```

### Parallel Recorder (`rf_recorder_parallel.py`)

For advanced users who want direct control over recording parameters:

```bash
# Basic recording
python3 rf_recorder_parallel.py -f 2.44e9 -s 5e6 -t 300 -o my_capture -c zstd --no-viz

# With visualization  
python3 rf_recorder_parallel.py -f 2.44e9 -s 5e6 -t 300 -o my_capture -c zstd

# High-performance settings
python3 rf_recorder_parallel.py -f 2.44e9 -s 10e6 -t 300 -o capture \
    -c zstd --compression-level 1 --chunk-size 4194304 --threads 6 --no-viz
```

### Replay Tool (`rf_replay_tool.py`)

#### Data Analysis

```bash
# Analyze captured data
python3 rf_replay_tool.py --file my_capture.zst --freq 2.44e9 --rate 5e6 --analyze-only

# Browse dataset contents
python3 rf_replay_tool.py --dataset rf_dataset_office_* --list-only
```

#### Safe Replay Testing

```bash
# Low power replay (start here)
python3 rf_replay_tool.py --file capture.zst --freq 2.44e9 --rate 5e6 --gain 5 --scale 0.1

# Continuous loop replay
python3 rf_replay_tool.py --file capture.zst --freq 2.44e9 --rate 5e6 --loop --delay 2
```

## File Structure

### Generated Dataset Structure

```
rf_dataset_coffee_shop_20241205_143022/
├── collection_summary.json                    # Metadata for entire collection
├── replay_dataset.py                         # Auto-generated replay script  
├── wifi_2_4_ghz_ch1_20241205_143022.zst      # WiFi Channel 1 data
├── wifi_2_4_ghz_ch1_20241205_143022.meta     # Channel 1 metadata
├── wifi_2_4_ghz_ch6_20241205_143022.zst      # WiFi Channel 6 data
├── wifi_2_4_ghz_ch6_20241205_143022.meta     # Channel 6 metadata
├── wifi_5_ghz_ch36_20241205_143022.zst       # 5 GHz data
├── other_bands_fm_radio_20241205_143022.zst  # FM radio data
└── ... (additional frequency captures)
```

### Metadata Files

Each `.meta` file contains:
```
center_frequency_hz=2437000000
sample_rate_hz=5000000  
gain_db=30.0
duration_seconds=300.12
samples=1500600000
compression=zstd
timestamp=2024-12-05T14:30:22
```

### Collection Summary

`collection_summary.json` contains:
```json
{
  "collection_start": "20241205_143022",
  "location": "coffee_shop", 
  "mode": "detailed_capture",
  "settings": {"sample_rate": 5000000, "duration": 300, "gain": 30},
  "captures": [...]
}
```

## Troubleshooting

### Common Issues

#### "No devices found" Error
```bash
# Check USRP connection
uhd_find_devices

# Check permissions  
groups | grep usrp

# If not in usrp group:
sudo usermod -a -G usrp $USER
# Log out and back in
```

#### Overflow Errors (Many 'O' Characters)
```bash
# Test lower sample rates
python3 rf_dataset_collector.py --test-rates

# Optimize system
sudo cpupower frequency-set -g performance
echo 256 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb

# Use conservative settings
python3 rf_dataset_collector.py --location "test" --mode quick_survey
```

#### Low Signal Power (< -50 dB)
```bash
# Use higher gain (edit collection modes in script)
# Capture closer to signal sources  
# Verify antenna connections
# Check for interference or shielding
```

#### UHD FFT Visualization Issues
```bash
# Run without visualization
python3 rf_dataset_collector.py --location "test" --mode quick_survey --no-viz

# Test standalone visualization
uhd_fft -f 2.44e9 -s 5e6 -g 30
```

### Performance Optimization

#### For Higher Sample Rates
- Use fastest compression: `--compression-level 1`
- Increase chunk size: `--chunk-size 4194304`  
- Use more threads: `--threads 8`
- Disable visualization: `--no-viz`
- Use SSD storage
- Close unnecessary applications

#### For Long Collections
- Use moderate sample rates (1-2 MS/s)
- Enable compression to save disk space
- Monitor disk space during collection
- Use `screen` or `tmux` for persistent sessions

## Legal and Safety Considerations

### ⚠️ Important Warnings

#### Legal Compliance
- **Licensed bands**: Many frequencies require licenses to transmit
- **WiFi replay**: Transmitting captured WiFi data may violate regulations
- **Interference**: RF transmission can disrupt legitimate communications
- **Check local laws**: RF regulations vary by country/region

#### Safe Testing Practices

**For Replay Testing:**
1. **Use dummy loads** instead of antennas when possible
2. **Start with very low power**: `--gain 5 --scale 0.1`  
3. **Use RF attenuators** (20-30 dB) between TX and RX
4. **Test in shielded environments** when possible
5. **Monitor for interference** to licensed services

**Recommended Test Setup:**
```
USRP_TX --[Attenuator 30dB]-- Cable --[Attenuator 20dB]-- USRP_RX
```

#### Analysis-Only Alternative
```bash
# Analyze data without any transmission
python3 rf_replay_tool.py --file data.zst --freq 2.44e9 --rate 5e6 --analyze-only
```

### Best Practices

1. **Start with analysis-only** to understand your data
2. **Use minimum necessary power** for testing
3. **Coordinate with spectrum management** for research use
4. **Document your testing** for regulatory compliance
5. **Consider amateur radio frequencies** if you're licensed
6. **Use proper RF safety practices** around transmitting equipment

## Frequency Coverage

### Default Frequency Plan

**2.4 GHz WiFi Band:**
- Channel 1: 2.412 GHz
- Channel 6: 2.437 GHz  
- Channel 11: 2.462 GHz
- Band Center: 2.44 GHz

**5 GHz WiFi Band:**
- Channel 36: 5.18 GHz
- Channel 100: 5.5 GHz
- Channel 149: 5.745 GHz

**Other Bands:**
- FM Radio: 100.1 MHz
- ISM 433: 433.92 MHz
- ISM 868: 868 MHz
- Cellular: 850 MHz

### Sample Rate Coverage

At 5 MS/s sample rate:
- **Bandwidth**: ±2.5 MHz around center frequency
- **WiFi channel coverage**: ~25% of 20 MHz channel
- **Sufficient for**: Signal presence, power analysis, spectral characteristics
- **Limitations**: Cannot decode full protocols, limited bandwidth

## Contributing

To customize for your specific needs:

1. **Edit frequency lists** in `rf_dataset_collector.py`
2. **Modify collection modes** (sample rates, durations, gains)
3. **Add custom analysis** in `rf_replay_tool.py`
4. **Extend metadata** collection for your research

## Support

For issues and questions:

1. **Check this README** for common solutions
2. **Verify hardware setup** with basic UHD tools
3. **Test with known-good configurations** first
4. **Document your specific setup** when reporting issues

## License

This toolkit is provided for educational and research purposes. Users are responsible for compliance with all applicable laws and regulations regarding RF transmission and spectrum usage.

---

**Version**: 1.0  
**Last Updated**: December 2024  
**Compatible**: Ubuntu 20.04+, UHD 4.0+, USRP B200/B205 series
