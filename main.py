import sys,os
from pathlib import Path
import shutil
import subprocess
import sys
import argparse

def main(args):
    Path('.nb_args').open('w').write(" ".join(sys.argv))
    os.environ['NB_EXEC_ARGS'] = "True"
    print("Tip: Track progress by opening ./progress.log file")
    print("When encountering an issue, make sure you provide the following pieces of information:"
          """"
        - [ ] Provide OS information, windows, linux, etc, and RAM size size  (8GB, 16GB, etc).
        - [ ] Add the result of running `git log`.
        - [ ] Add `progress.log` file.
        - [ ] Add the problematic video file to the issue.
        - [ ] Add exact command(s) you used to run to get the issue, as well as the printed output.
        - [ ] Make sure you can replicate the issue while following the above results.
        """)
    os.system(f'jupyter nbconvert --execute {args.notebook} --to html \
         --output result.html --ExecutePreprocessor.timeout=-1 -y')
    return None

if __name__ == '__main__':
    args = argparse.ArgumentParser()
    args.add_argument('--notebook', type=str, default='main.ipynb')
    args,_ = args.parse_known_args()
    main(args)