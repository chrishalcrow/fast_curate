import numpy as np

def compute_autocorrelograms(spike_times, window_ms, bin_ms, fs):

    window_size = int(round(fs*window_ms / 2 * 1e-3))
    bin_size = int(round(fs*bin_ms * 1e-3))
    window_size -= window_size % bin_size
    num_bins = 2*int(window_size/bin_size)

    num_half_bins = int(num_bins // 2)
    correlograms = np.zeros(num_bins, dtype=np.int64)

    start_j = 0
    for i in range(spike_times.size):
        for j in range(start_j, spike_times.size):

            if i == j:
                continue

            diff = spike_times[i] - spike_times[j]

            # When the diff is exactly the window size, keep going
            # without iterating start_j in case this spike also has
            # other diffs with other units that == window size.
            if diff == window_size:
                continue

            # if the time of spike i is more than window size later than
            # spike j, then spike i + 1 will also be more than a window size
            # later than spike j. Iterate the start_j and check the next spike.
            if diff > window_size:
                start_j += 1
                continue

            # If the time of spike i is more than a window size earlier
            # than spike j, then all following j spikes will be even later
            # i spikes and so all more than a window size earlier. So move
            # onto the next i.
            if diff < -window_size:
                break

            bin = diff // bin_size

            correlograms[num_half_bins + bin] += 1

    return correlograms, np.arange(-window_size, window_size + bin_size, bin_size)* 1e3/fs



