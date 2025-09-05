import sys
import matplotlib.pyplot as plt
import numpy as np


def noise_floor_tracker(nfft, alpha_up=0.999, alpha_down=0.5):
    # Initialize state
    noise_psd = None

    chunk = yield np.zeros(nfft)

    while True:
        S = chunk
        if noise_psd is None:
            noise_psd = S
        else:
            # where S < current: update downwards faster
            down_mask = S < noise_psd
            noise_psd[down_mask] = (
                alpha_down * noise_psd[down_mask] + (1 - alpha_down) * S[down_mask]
            )
            # where S >= current: let it creep up slowly
            up_mask = ~down_mask
            noise_psd[up_mask] = (
                alpha_up * noise_psd[up_mask] + (1 - alpha_up) * S[up_mask]
            )

        chunk = yield noise_psd

def read_complex_chunks(filename, chunk_size, overlap=0.0):

    data = np.memmap(filename, dtype=np.complex64, mode='r')
    for start in range(0, len(data) - chunk_size + 1, int(chunk_size * (1 - overlap))):
        yield data[start:start + chunk_size]


def plot_spectrum(ax, freqs, power, noise_floor_db):
        ax.clear()
        ax.plot(freqs / 1e6, power, label="Avg Power (dB/Hz)")
        ax.set_xlabel("Frequency (MHz)")
        ax.set_ylabel("Power (dB/Hz)")
        ax.set_title("RF Spectrum Analyzer")
        ax.legend()
        # plot noise floor line
        ax.axhline(noise_floor_db, color='r', linestyle='--', label='Noise Floor')
        if np.max(power) > noise_floor_db + 20:
            ax.axhline(y=np.max(power), color='g', linestyle='--', label='Signal Peak')
        ax.set_ylim(-100, 10)
        plt.pause(0.0005)



def run_analysis(filename, fs, chunk_size=1024, overlap=0.5, plot=False):

    avg_Sxx = None
    smoothing = 0.5
    noise_tracker = noise_floor_tracker(chunk_size)
    next(noise_tracker)  # prime the generator
    fig, ax = plt.subplots()
    for chunk in read_complex_chunks(filename, chunk_size, overlap):
        # Compute FFT
        N = len(chunk)
        w = np.blackman(N)
        fft_result = np.fft.fft(chunk * w)
        fft_freqs = np.fft.fftshift(np.fft.fftfreq(N, d=1/fs))
        Sxx = (np.abs(fft_result)**2) / (fs * sum(w**2))
        # linearly average with previous
        if avg_Sxx is None:
            avg_Sxx = Sxx
        else:
            avg_Sxx = smoothing * avg_Sxx + (1 - smoothing) * Sxx

        power = 10 * np.log10(avg_Sxx * fs / N)
        power = np.fft.fftshift(power)
        
        noise_floor = noise_tracker.send(avg_Sxx)
        noise_floor_db = np.median(10 * np.log10(noise_floor * fs / N))

        if plot:
            plot_spectrum(ax, fft_freqs, power, noise_floor_db)

def main(args: list[str]):
    print("RF Analyzer script executed with arguments:", args)

    filename = args[0]
    run_analysis(filename, fs=1e6, chunk_size=1024, overlap=0.5)


if __name__ == "__main__":
    main(sys.argv[1:])
