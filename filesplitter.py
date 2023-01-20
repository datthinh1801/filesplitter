import argparse
import hashlib
import math
from pathlib import Path
from colorama import Fore, Style
from configparser import ConfigParser

VERBOSE = False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Split a large file into smaller files (split in parts or chunk size) or merge file parts into the large file.",
    )
    subparsers = parser.add_subparsers(title="operation", dest="operation")
    split_parser = subparsers.add_parser("split")
    split_parser.add_argument(
        "-f",
        "--file",
        help="File to split",
    )
    split_parser.add_argument(
        "-p", "--parts", help="the number of parts to split into", type=int, default=0
    )
    split_parser.add_argument(
        "-cs",
        "--chunk-size",
        help="the chunk size (in bytes) of each part to split into",
        type=int,
        default=0,
    )
    split_parser.add_argument(
        "-R",
        "--remove",
        help="remove the original file",
        dest="remove",
        action="store_true",
    )
    split_parser.add_argument("-v", help="verbose", dest="verbose", action="store_true")

    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument(
        "-d", "--dir", help="directory containing files to merge", dest="dir"
    )
    merge_parser.add_argument("-v", help="verbose", dest="verbose", action="store_true")
    return parser.parse_args()


def split_file(
    filename: str, parts: int = 0, chunk_size: int = 0, remove: bool = False
) -> bool:
    if parts == 0 and chunk_size == 0:
        return False

    current_dir = Path(".").resolve()
    filepath = current_dir / filename
    filesuffix = "".join(filepath.suffixes)
    basename = filepath.name.removesuffix("".join(filepath.suffixes))
    filesize = filepath.stat().st_size
    filebytes = filepath.read_bytes()
    filehash = hashlib.sha256(filebytes).hexdigest()

    verbose(f"[i] Source file: {filepath}")
    verbose(f"[i] File size: {filesize}")
    verbose(f"[i] File hash: {filehash}")

    if parts > 0:
        chunk_size = math.ceil(filesize / parts)
    else:
        parts = math.ceil(filesize / chunk_size)
    verbose(f"[i] Parts: {parts}")
    verbose(f"[i] Segment size: {chunk_size}")
    verbose(f"[i] Creating {basename} directory...")
    subdir = current_dir / basename
    if subdir.is_dir():
        for path in subdir.glob("*"):
            path.unlink()
        subdir.rmdir()
    subdir.mkdir()

    verbose(f"[i] Splitting files...")
    for part in range(parts):
        buffer = filebytes[part * chunk_size : (part + 1) * chunk_size]
        part_filepath = subdir / f"{filename}.{part}.prt"
        part_filepath.write_bytes(buffer)

    hashpath = subdir / f"{filename}.hash"
    hashpath.write_text(filehash)

    if remove:
        verbose(f"[i] Removing the original file...")
        filepath.unlink(missing_ok=True)


def merge(dirname: str):
    dirpath = Path(".") / dirname
    if not dirpath.is_dir():
        return False

    filebytes = b""
    filepath = None
    verbose(f"[i] Merging files...")
    for path in get_sorted_files(dirpath):
        verbose(f"[i] Reading {path.name}...")
        # infer the original filename from the first splitted file
        if filepath is None:
            filename = f"{path.name.split('.')[0]}{''.join(path.suffixes[:-2])}"
            filepath = Path(".") / filename

        buffer = path.read_bytes()
        filebytes += buffer

    verbose(f"[i] Writing data to {filepath.name}...")
    filepath.write_bytes(filebytes)

    verbose(f"[i] Verifying file hash...")
    ver_filehash = hashlib.sha256(filepath.read_bytes()).hexdigest()
    filehashpath = list(dirpath.glob("*hash"))[0]
    filehash = filehashpath.read_text()
    if ver_filehash == filehash:
        verbose(f"[i] Hash verification succeeded!")
    else:
        verbose(f"[x] Hash verification failed!")


def get_part_no(filepath: Path):
    return int(filepath.suffixes[-2].strip("."))


def get_sorted_files(dirpath: Path):
    filepaths = sorted(dirpath.glob("*prt"), key=lambda path: get_part_no(path))
    return filepaths


def verbose(msg: str):
    global VERBOSE

    if VERBOSE:
        print(msg)


def main():
    global VERBOSE

    args = parse_args()
    if args.verbose:
        VERBOSE = True

    if args.operation == "split":
        split_file(args.file, args.parts, args.chunk_size, args.remove)
    elif args.operation == "merge":
        merge(args.dir)


if __name__ == "__main__":
    main()
