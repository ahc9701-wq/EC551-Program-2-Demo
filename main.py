
import sys

from synthesis.cli import run


def main():
    if len(sys.argv) > 1:
        initial_file = sys.argv[1]
    else:
        initial_file = None

    run(initial_file)


if __name__ == "__main__":
    main()
