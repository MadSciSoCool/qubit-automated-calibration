import numpy as np
from scipy.optimize import curve_fit
from scipy.interpolate import splrep, splev
from sklearn.decomposition import PCA


# general processing

def find_index(array, value):
    ''' find index of a certain (closest) value(s) in a array
    '''
    array = np.array(array)
    if not np.iterable(value):
        index = np.argmin(np.absolute(array - value))
        return index
    else:
        value = np.array(value)
        index = []
        for value in value:
            index.append(np.argmin(np.absolute(array - value)))
        return np.array(index)


def interpolate(x, y, xn):
    """interpolate with b-spline (why?)"""
    rp = splrep(x, y, s=0)
    yn = splev(xn, rp, der=0)
    return yn


def pca(x, y):
    pca = PCA(n_components=2)
    X = np.vstack([x, y]).T
    pca.fit(X)
    PCA(copy=True, n_components=2, whiten=False)
    Xd = pca.transform(X)
    return Xd.transpose()[0], Xd.transpose()[1]


def get_offset(y, bin_num=None):
    if bin_num is None:
        bin_num = int(np.size(y)/10)
    bins = np.linspace(np.amin(y), np.amax(y), bin_num)
    hist = np.histogram(y, bins=bins)[0]
    bins = 0.5*(bins[1:] + bins[:-1])
    mode_idx = np.argmax(hist)
    offset = bins[mode_idx]
    return offset


def power_spectrum(t, y):
    dx = t[1]-t[0]
    N = t.size
    f = np.fft.fftfreq(N, dx)
    f = np.fft.fftshift(f)
    yf = np.fft.fft(y)
    yf = np.fft.fftshift(yf)/float(N)
    p = np.absolute(yf)**2
    return f, p

# functions


def linear(x, a, b):
    return x * a + b


def lorentzian(x, x0, a, gamma, offset):
    return a / (((x-x0) / (gamma/2))**2 + 1) + offset


def sinusoidal(x, a, freq, phi, offset):
    return a*np.cos(2.*np.pi*freq*x-phi)+offset


def exponential(x, a, decay, offset):
    return a*np.exp(decay*x)+offset


def damped_sinusoidal(x, a, gamma, freq, phi, offset):
    return a*np.exp(gamma*x)*np.cos(2.*np.pi*freq*x-phi) + offset


# fitting initials


def linear_p0(x, y):
    a = (y[-1]-y[0])/(x[-1]-x[0])
    b = y[0]-a*x[0]
    return (a, b)


def lorentzian_p0(x, y):
    offset = get_offset(y)
    ind_max = np.argmax(np.absolute(y-offset))
    idx_hwhm = np.argmin(np.absolute(y - (y[ind_max] + offset)/2.0))
    gamma = 2.0 * np.absolute(x[ind_max]-x[idx_hwhm])
    a = y[ind_max] - offset
    return (x[ind_max], a, gamma, offset)


def sinusoidal_p0(x, y):
    N = x.size
    fr, ps = power_spectrum(x, y)
    fr_pos = fr[N//2+1:]
    ps_pos = ps[N//2+1:]
    try:
        popt, pcov = curve_fit(
            fr_pos, ps_pos, p0=lorentzian_p0(fr_pos, ps_pos))
        freq = popt[0]
    except:
        freq = fr_pos[np.argmax(ps_pos)]
    offset = np.average(y[N//2:])
    x_max = x[np.argmax(y)]
    phi = 2.*np.pi*freq*x_max
    a = np.absolute(np.amax(y)-offset)
    return (a, freq, phi, offset)


def exponential_p0(x, y):
    num = int(np.size(x)/10)
    popt1, pcov1 = curve_fit(linear, x[0:num], y[0:num])
    popt2, pcov2 = curve_fit(linear, x[-num:], y[-num:])
    if np.absolute(popt1[0]) > np.absolute(popt2[0]):
        offset = y[-1]
        a = y[0]-offset
        decay = popt1[0]/a
        p0 = (a, decay, offset)
    else:
        offset = y[0]
        a = y[-1]-offset
        decay = popt1[0]/a
        p0 = (a, decay, offset)
    return p0


def damped_sinusoid_p0(x, y):
    N = x.size
    fr, ps = power_spectrum(x, y)
    fr_pos = fr[N//2+1:]
    ps_pos = ps[N//2+1:]
    freq = fr_pos[np.argmax(ps_pos)]
    f_int = np.linspace(fr_pos[0], fr_pos[-1], 10001)
    p_int = interpolate(fr_pos, ps_pos, f_int)
    ind = find_index(p_int, np.amax(ps_pos)/2)
    gamma = -2*np.pi*np.absolute(freq - f_int[ind])
    offset = np.average(y)
    x_max = x[np.argmax(y)]
    phi = 2.*np.pi*freq*x_max
    a = np.absolute(np.amax(y)-offset)*np.exp(-gamma*x_max)
    return (a, gamma, freq, phi, offset)
