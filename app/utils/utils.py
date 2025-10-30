from matplotlib import pyplot as plt


def setupPlot(logarithmic=True):
    """
    Helper method to set up the plots with correct axis labels and such
    :param logarithmic: whether the plot vertical axis should be logarithmic or not
    :return: plot object
    """
    fig = plt.figure(figsize=(5, 4), dpi=250)
    ax_1 = fig.add_subplot(111)

    if logarithmic:
        ax_1.set_yscale('log')
    ax_1.set_xlabel('Frequency [MHz]', fontsize=18)
    ax_1.set_ylabel(r'$\mid Z\mid [\Omega]$', fontsize=18)
    ax_1.tick_params(axis='x', labelsize=15)
    ax_1.tick_params(axis='y', labelsize=15)

    plt.tight_layout()

    return ax_1


def plotSet(plot, dataset, color="blue", style="-", label: str = "", peaks: dict = None, peak_color="red"):
    """
    Helper method to add a set of datapoints to the plot object returned by `setupPlot`
    :param plot: the plot object
    :param dataset: the dataset containing the datapoints to add, as a dictionary-like object with keys 'frequency' and
    'impedance' as x and y axis values
    :param color: color of points
    :param style: style of line
    :param label: label of dataset for the legend
    :param peaks: dictionary containing the peaks of the dataset if you desire to plot them, keys are "x" and "y"
    :param peak_color: color of peak points
    :return: nothing
    """
    plot.plot(dataset["frequency"], dataset["impedance"], style,
              markersize=1,
              linewidth=2,
              color=color,
              label=label)
    if peaks is not None:
        plot.scatter(x=peaks["x"], y=peaks["y"], color=peak_color, marker="x")


def materialExists(materials, name):
    """
    Helper method to check if a material exists
    :param materials: material registry
    :param name: name of material to search for
    :return: whether the material exists
    """
    return name in materials.index


def findPeaks(dataset, kernel, threshold):
    """
    Helper method to find the peaks of the dataset. We found it to work better than the standard scikit function under
    certain circumstances. It works by using a "kernel", what that means is that we look at a "slice" of the dataset of
    size kernel and we search peaks in that region, we then slide this region forward, kinda like sliding a window
    along the horizontal axis and looking only at the points inside it. The name "kernel" comes from convolution
    operations of images. Whiting this region we identify the smallest (we talk about peaks, but we are actually looking
    for minima to find the resonance frequencies, so technically it would be valleys we are looking for, but the idea
    is the same) point excluding the leftmost and rightmost ones. If this point is larger than both the right most and
    leftmost points then we skip this region, otherwise we calculate the absolute percentage of the difference
    between this minimum point and the leftmost and rightmost points. If both of these differences are larger than the
    threshold value, then we store the minimum point as a peak (in a dictionary to avoid repetitions). \n
    Play around with the kernel and threshold values to get what you need. As a rule of thumb, a larger kernel makes
    the search less sensitive against many peaks close to each other, and a larger threshold makes the search less
    sensitive against small peaks.
    :param dataset: dataset to search for peaks
    :param kernel: see function description
    :param threshold: see function description
    :return: dictionary containing the peaks with keys 'x' and 'y'
    """
    x = dataset["frequency"]
    y = dataset["impedance"]
    peaks = set()

    for i in range(len(x) - kernel):
        left = y[i]
        right = y[i + kernel]
        mx = None
        mxi = -1

        for j in range(1, kernel - 1):
            k = j + i
            if mx is None:
                mx = y[k]
                mxi = k
            elif mx > y[k]:
                mx = y[k]
                mxi = k

        if left > mx and right > mx:
            rl = abs(abs(mx / left) * 100 - 100)
            rr = abs(abs(mx / right) * 100 - 100)
            if rl > threshold and rr > threshold:
                peaks.add(mxi)

    return {"x": [x[i] for i in peaks], "y": [y[i] for i in peaks]}
