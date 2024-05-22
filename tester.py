import subprocess

def run_test(n):
    # Run receiver.py
    receiver_process = subprocess.Popen(
        ["python3", "receiver.py", "-p", "9999", "-ip", "127.0.0.1", "-o", "output.txt"]
    )

    # Run sender.py with current value of n
    subprocess.run(
        ["python3", "sender.py", "-p", "9999", "-ip", "127.0.0.1", "-t", str(n), "-o", "output.txt"]
    )

    # Terminate receiver process after sender finishes
    receiver_process.terminate()
    receiver_process.wait()

    # Check if output.txt matches random.txt
    with open("random.txt", "r") as f_random, open("output.txt", "r") as f_output:
        random_content = f_random.read()
        output_content = f_output.read()
        assert random_content == output_content, f"Files do not match for n={n}"


def main():
    for n in range(1, 3):
        run_test(n)
        print(f"Test passed for n={n}")


if __name__ == '__main__':
    main()
