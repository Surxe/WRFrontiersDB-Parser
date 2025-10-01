# Add two levels of parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import run_process

from loguru import logger

def main():
    pass

if __name__ == "__main__":
    main()