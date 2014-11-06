import numpy as np
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
from scipy.ndimage.filters import maximum_filter
from scipy.ndimage.morphology import generate_binary_structure, iterate_structure, binary_erosion
import hashlib


WINDOW_SIZE = 4096 # granularity of chunks
SAMPLE_RATE = 44100 # by nyquist or whatever
OVERLAP_RATIO = 0.5 # amount our chunks can overlap

def get_fingerprints(samples):
    """Give it a mono stream, yo
    """
    spectrogram = get_spectrogram(samples)

    # get peaks
    peaks = get_peaks(spectrogram)

    # hash them!

    fingerprints = hash_peaks(peaks)

    return fingerprints


def get_spectrogram(samples):
    spectrogram = mlab.specgram(samples,
                               NFFT=WINDOW_SIZE,
                               Fs=SAMPLE_RATE,
                               window=mlab.window_hanning,
                               noverlap = int(WINDOW_SIZE * OVERLAP_RATIO))[0]
    # log the result
    spectrogram = 10 * np.log10(spectrogram)

    # np.inf is terrible, replace with zeros.
    spectrogram[spectrogram == -np.inf] = 0

    return spectrogram



AMPLITUDE_THRESHOLD = 20

def get_peaks(spectrogram):
    """Gets all the peaks from this spectrogram.
    """
    # generate the filter pattern (neighborhoods)
    peak_filter = generate_binary_structure(2, 1)
    neighborhood = iterate_structure(peak_filter, 20).astype(int)

    # set each point equal to the maximum in it's neighborhood
    local_max = maximum_filter(spectrogram, footprint=neighborhood)

    # check where the 'local max' is equal to our original values.
    # these are our peaks.
    peaks = local_max==spectrogram

    # filter out background around the peaks:
    # http://docs.scipy.org/doc/scipy-0.14.0/reference/generated/scipy.ndimage.morphology.binary_erosion.html
    background = (spectrogram == 0)
    eroded = binary_erosion(background,
                            structure=neighborhood,
                            border_value=1)
    actual_peaks = peaks - eroded

    # problem here is that we see lots of peaks in LOW areas. Let's
    # filter out the low ones.
    amplitudes = spectrogram[actual_peaks].flatten()
    y, x = actual_peaks.astype(type).nonzero()
    all_peaks = zip(x, y, amplitudes)

    filtered_peaks = [p for p in all_peaks if p[2] > AMPLITUDE_THRESHOLD]

    return filtered_peaks

FINGERPRINT_PAIR_DISTANCE = 19
FINGERPRINT_TIME_DELTA = 10

def hash_peaks(filtered_peaks):
    sorted_peaks = sorted(filtered_peaks, key=lambda p: p[0])
    # of the form (f1, f2, time_delta)
    fingerprints = []
    for i, peak in enumerate(sorted_peaks):
        # get all peaks within `fingerprint_pairs` of the current peak
        potential_pairs = sorted_peaks[i+1:i+FINGERPRINT_PAIR_DISTANCE]
        # get rid of the ones that are too far away in time
        potential_pairs = [p for p in potential_pairs if p[0] - peak[0] < FINGERPRINT_TIME_DELTA]
        # create the (f1, f2, time_delta) tuples
        prints = [(peak[1], p[1], (p[0] - peak[0])) for p in potential_pairs]
        fingerprints.extend(prints)

    hashes = []
    for fprint in fingerprints:
        h = hashlib.md5('{0}|{1}|{2}'.format(fprint[0], fprint[1], fprint[2]))
        hashes.append(h.hexdigest())
    return hashes
