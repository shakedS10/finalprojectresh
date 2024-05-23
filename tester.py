import argparse
import subprocess
import time

import constants as c


def run_test(n):
    # Run receiver.py
    receiver_process = subprocess.Popen(
        ["python3", "receiver.py"]
    )

    # Run sender.py with current value of n
    subprocess.run(
        ["python3", "sender.py", "-t", str(n), "-s", str(delay)]
    )

    # Terminate receiver process after sender finishes
    receiver_process.terminate()
    receiver_process.wait()
    time.sleep(c.testingInterval)
    # Check if output.txt matches random.txt
    with open("random.txt", "r") as f_random, open("output.txt", "r") as f_output:
        random_content = f_random.read()
        output_content = f_output.read()
        assert abs(len(random_content) - len(output_content)) <= loss


def main():
    arg_parser = argparse.ArgumentParser(description="A Receiver for QUIC-like packets.")
    arg_parser.add_argument("-d", "--delay", type=float, default=c.defaultDelay, help="The delay for sending data")
    arg_parser.add_argument("-t", "--threads", type=int, default=c.defaultStreamNumberTester, help="The maximum "
                                                                                                   "number of threads")
    arg_parser.add_argument("-l", "--loss", type=int, default=c.defaultLoss, help="The maximum loss")

    global delay
    delay = arg_parser.parse_args().delay

    global threads
    threads = arg_parser.parse_args().threads

    global loss
    loss = arg_parser.parse_args().loss

    for n in range(1, threads + 1):
        run_test(n)
        print(f"Test passed for n={n}")


if __name__ == '__main__':
    main()
