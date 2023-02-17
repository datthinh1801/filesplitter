""""
Recursively split files within a directory.
And recursively merge files within subdirectories into original files.
"""

import argparse
import shutil

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
    subparsers = parser.add_subparsers(title="operation", dest="operation")
    split_parser = subparsers.add_parser("split")
    split_parser.add_argument(
        "-d",
        "--dir",
        help="directory that contains files to split",
        dest="dir",
        required=True,
    )
    split_parser.add_argument(
        "-cs",
        "--chunk_size",
        help="the max size (in bytes) of each small file to split into",
        dest="chunk_size",
        type=int,
        default=0,
    )
    split_parser.add_argument(
        "-p",
        "--parts",
        help="the number of parts to split a file into",
        type=int,
        default=0,
        dest="parts",
    )
    split_parser.add_argument(
        "-R",
        "--remove",
        help="remove the original files",
        dest="remove",
        action="store_true",
    )
    split_parser.add_argument(
        "-igf",
        "--ignore-files",
        help="files to ignore (multiple files are separated by spaces)",
        dest="ignore_files",
        nargs="*",
    )
    split_parser.add_argument(
        "--compress",
        help="compress the splitted file on read",
        dest="compress",
        action="store_true",
    )

    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument(
        "-d",
        "--dir",
        help="directory that contains files to merge",
        dest="dir",
        required=True,
    )
    merge_parser.add_argument(
        "-igd",
        "--ignore-dirs",
        help="directories to ignore (multiple directories are separated by spaces)",
        dest="ignore_dirs",
        nargs="*",
    )
    merge_parser.add_argument(
        "-R",
        "--remove",
        help="remove the original files",
        dest="remove",
        action="store_true",
    )

    parser.add_argument("-v", help="verbose", dest="verbose", action="store_true")
    return parser.parse_args()


def collect_dirs(dirpath: Path, ignore_dirs: list[str]) -> list[Path]:
    """Collect directories within a directory that contain files to merge.

    Args:
        dirpath (Path): the Path object of the directory.
        ignore_dirs (list[str]): a list of directories to ignore.
    Returns:
        (list[Path]): a list of directory paths.
    """
    cur_dir = dirpath
    final_dirs = []
    queue = Queue()
    queue.put(cur_dir)
    ignore_paths = [Path(dirname).resolve() for dirname in ignore_dirs or []]
    while not queue.empty():
        cur_dir = queue.get()
        if cur_dir.resolve() in ignore_paths:
            continue

        # directory that only contains splitted files
        if (cur_dir / "config.ini").exists():
            final_dirs.append(cur_dir)
            continue

        # empty directory
        children = list(cur_dir.glob("*"))
        if len(children) == 0:
            continue

        subdirs = [subdir for subdir in children if subdir.is_dir()]
        for subdir in subdirs:
            queue.put(subdir)

    return final_dirs


def collect_files(dirpath: Path, ignore_files: list[str]) -> list[Path]:
    """Collect files to split within the directory.

    Args:
        dirpath (Path): the Path object of the directory.
        ignore_files (list[str]): a list of files to ignore
    Returns:
        (list[Path]): a list of file paths.
    """
    files = [path for path in dirpath.glob("**/*") if path.is_file()]
    ignore_filepaths = [Path(filename).resolve() for filename in ignore_files or []]
    final_filepaths = [
        final_file
        for final_file in files
        if final_file.resolve() not in ignore_filepaths
    ]
    final_filepaths = list(
        filter(
            lambda filepath: filepath.suffix != ".prt"
            and filepath.name != "config.ini",
            final_filepaths,
        )
    )
    return final_filepaths


def split_dir(
    dirname: Path or str,
    ignore_files: list,
    parts: int,
    chunks_size: int,
    remove: bool,
    compress: bool,
):
    """Split files within the given directory.

    Args:
        dirname (Path or str): the name of the directory.
        ignore_files (list): the name of files to ignore.
        parts (int): the number of parts to split a file into.
        chunks_size (int): the max size (in byte) of a small file to split into.
        remove (bool): remove the original files.
        compress (bool): compress the splitted files.
    """
    if isinstance(dirname, str):
        dirpath = Path(dirname)
    else:
        dirpath = dirname

    if not dirpath.is_dir():
        verbose(f"[x] {dirname} not exists!", Fore.RED)
        exit(1)

    filepath_list = collect_files(dirpath, ignore_files)
    for filepath in filepath_list:
        split_file(
            filepath,
            parts=parts,
            chunk_size=chunks_size,
            remove=remove,
            compress=compress,
        )
        print(shutil.get_terminal_size()[0] * "-")


def merge_dir(dirname: Path or str, ignore_dirs: list[str], remove: bool):
    """Merge all splitted files within the given directory into their original files.

    Args:
        dirname (Path or str): the name of the directory.
        ignore_dirs (list[str]): a list of directory names to ignore.
        remove (bool): remove the directory that contains splitted files.
    """
    if isinstance(dirname, str):
        dirpath = Path(dirname)
    else:
        dirpath = dirname

    if not dirpath.is_dir():
        verbose(f"[x] {dirname} not exists!", Fore.RED)
        exit(1)

    subdir_pathlist = collect_dirs(dirpath, ignore_dirs)
    for subdir_path in subdir_pathlist:
        merge(subdir_path, remove)
        print(shutil.get_terminal_size()[0] * "-")


def main():
    """Main routine of dirsplitter."""
    args = parse_args()
    dirpath = Path(args.dir)
    if not dirpath.is_dir():
        verbose(f"[x] {args.dir} not exists!", Fore.RED)
        return

    if args.operation == "split":
        split_dir(
            dirpath,
            args.ignore_files,
            args.parts,
            args.chunk_size,
            args.remove,
            args.compress,
        )
    elif args.operation == "merge":
        merge_dir(dirpath, args.ignore_dirs, args.remove)


if __name__ == "__main__":
    main()
