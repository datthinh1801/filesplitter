""""
Recursively split files within a directory.
And recursively merge files within subdirectories into original files.
"""

import argparse

from pathlib import Path
from queue import Queue

from colorama import Fore

from filesplitter import split_file, merge, verbose


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Recursively split large files within a directory into smaller files or \
        recursively merge small files into larger files within a directory."
    )
    parser.add_argument(
        "-op",
        "--operation",
        help="operation to perform",
        choices=["split", "merge"],
        dest="operation",
        required=True,
    )
    parser.add_argument(
        "-d", "--dir", help="directory to split or merge", dest="dir", required=True
    )
    parser.add_argument(
        "-cs",
        "--chunk_size",
        help="the max size (in bytes) of each small file to split into",
        dest="chunk_size",
        type=int,
        default=0,
    )
    parser.add_argument(
        "-p",
        "--parts",
        help="the number of parts to split a file into",
        type=int,
        default=0,
        dest="parts",
    )
    parser.add_argument(
        "-R",
        "--remove",
        help="remove the original files",
        dest="remove",
        action="store_true",
    )

    parser.add_argument("-v", help="verbose", dest="verbose", action="store_true")
    return parser.parse_args()


def collect_dirs(dirpath: Path):
    """Collect subdirectories of small files within a directory.

    Args:
        dirpath (Path): the Path object of the directory.
    """
    cur_path = dirpath
    final_dirs = []
    queue = Queue()
    queue.put(cur_path)
    while not queue.empty():
        cur_path = queue.get()
        children = list(cur_path.glob("*"))
        if len(children) == 0:
            continue

        subdirs = [subdir for subdir in children if subdir.is_dir()]
        if len(subdirs) > 0:
            for subdir in subdirs:
                queue.put(subdir)
        else:
            final_dirs.append(cur_path)
    return final_dirs


def main():
    """Main routine of dirsplitter."""
    args = parse_args()
    dirpath = Path(args.dir)
    if not dirpath.is_dir():
        verbose("f[x] {args.dir} not exists!", Fore.RED)
        return
    if args.operation == "split":
        filepath_list = [
            filepath for filepath in dirpath.glob("**/*") if filepath.is_file()
        ]

        for filepath in filepath_list:
            split_file(
                filepath,
                parts=args.parts,
                chunk_size=args.chunk_size,
                remove=args.remove,
            )
            print("-" * 20)
    elif args.operation == "merge":
        subdirpath_list = collect_dirs(dirpath)
        for subdirpath in subdirpath_list:
            merge(subdirpath, remove=args.remove)
            print("-" * 20)


if __name__ == "__main__":
    main()
