# coding=utf-8
import sys
import subprocess
from subprocess import Popen, PIPE
from operator import sub

CMD = [
    '/usr/bin/ssh',
    '-t',
    '-T',
    '-i',
    '/Users/edhurtig/.ssh/id_rsa',
    'root@10.0.0.80',
    '~/MPU6050-Pi-Demo/demo_raw'
]

ZERO_OFFSET_SAMPLES = 100
ZERO_OFFSET_BIAS = 0.33


def get_samples(proc):
    """Reads in from the given process stdout a line of data.
    The line should be formatted as follows:

        a/g:  -1332   -648  14704     -421   -145   -158

    which is interpretted as:
        IGNORED X Y Z OMEGA PHI KAPPA
    """
    while True:
        line = proc.stdout.readline()

        if line:
            try:
                return [float(x) for x in line.split()[1:]]
            except ValueError as e:
                pass


def forward(output, samples):
    """
    Writes the formatted data to the output

    The samples are assumed to be 16384 LSB/g and 131 LSB/deg/sec accuracy
    """
    samples[0] /= 16384.0
    samples[1] /= 16384.0
    samples[2] /= 16384.0
    samples[3] /= 131.0
    samples[4] /= 131.0
    samples[5] /= 131.0
    samples[6] = samples[6] / 340.0 + 36.53
    names = ['x', 'y', 'z', u'ω', u'φ', u'κ', u'temp']

    strs = [str(a) for a in samples]

    print(' '.join(strs))

    data = u' '.join([u'='.join(list(b)) for b in zip(names, strs)])
    print(data)

    output.write((data + u"\n").encode('utf-8'))
    output.flush()


def main():
    """ Main function """
    if len(sys.argv) != 2:
        print("Usage: {} <output>".format(sys.argv[0]))
        sys.exit(1)

    offsets = [0.0]*7
    sample_size = 0
    with open(sys.argv[1], "w+") as output:
        print(' '.join(CMD))
        proc = Popen(CMD, stdout=PIPE)
        while True:
            print("... Restart")
            try:
                while True:

                    samples = get_samples(proc)

                    if sample_size < ZERO_OFFSET_SAMPLES:
                        for i, e in enumerate(offsets):
                            offsets[i] = samples[i] * ZERO_OFFSET_BIAS + \
                                         e * (1 - ZERO_OFFSET_BIAS)
                        print("Converging Offsets: {} {}".format(sample_size,
                                                                 offsets))
                    else:
                        forward(output, map(sub, samples, offsets))
                    sample_size += 1
            except (IndexError) as e:
                print(e)
                raise e
                pass


if __name__ == "__main__":
    main()
