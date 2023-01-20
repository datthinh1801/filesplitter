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
    split_parser.add_argument("-f", "--file", help="File to split", dest="file")
    split_parser.add_argument(
        "-p",
        "--parts",
        help="the number of parts to split into",
        type=int,
        default=0,
        dest="parts",
    )
    split_parser.add_argument(
        "-cs",
        "--chunk-size",
        help="the chunk size (in bytes) of each part to split into",
        type=int,
        default=0,
        dest="chunk_size",
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
    merge_parser.add_argument(
        "-R",
        "--remove",
        help="remove the directory",
        dest="remove",
        action="store_true",
    )
    merge_parser.add_argument("-v", help="verbose", dest="verbose", action="store_true")
    return parser.parse_args()


def split_file(
    filename: str, parts: int = 0, chunk_size: int = 0, remove: bool = False
) -> bool:
    if parts == 0 and chunk_size == 0:
        verbose(f"[x] Parts and chunk size cannot both be 0!", Fore.RED)
        return False

    current_dir = Path(".").resolve()
    filepath = current_dir / filename
    filesuffix = "".join(filepath.suffixes)
    basename = filepath.name.removesuffix("".join(filepath.suffixes))
    filesize = filepath.stat().st_size
    filehash = hashlib.sha256(filepath.read_bytes()).hexdigest()

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
    remove_dir(subdir)
    subdir.mkdir()

    verbose(f"[i] Splitting files...")
    with filepath.open("rb") as f:
        for part in range(parts):
            chunk = f.read(chunk_size)
            part_filepath = subdir / f"{filename}.{part}.prt"
            with part_filepath.open("wb") as fp:
                fp.write(chunk)

    verbose(f"[i] Writing hash...")
    hashpath = subdir / f"{filename}.hash"
    hashpath.write_text(filehash)

    if remove:
        verbose(f"[i] Removing the original file...")
        filepath.unlink(missing_ok=True)
    verbose("[+] Finish!")


def merge(dirname: str, remove: bool = False):
    dirpath = Path(".") / dirname
    if not dirpath.is_dir():
        verbose(f"[x] Directory not exists!", Fore.RED)
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
        verbose(f"[x] Hash verification failed!", Fore.RED)
    if remove:
        remove_dir(dirpath)


def remove_dir(dirpath: Path):
    if dirpath.is_dir():
        for path in dirpath.glob("*"):
            path.unlink()
        dirpath.rmdir()


def get_part_no(filepath: Path):
    return int(filepath.suffixes[-2].strip("."))


def get_sorted_files(dirpath: Path):
    filepaths = sorted(dirpath.glob("*prt"), key=lambda path: get_part_no(path))
    return filepaths


def verbose(msg: str, color=Fore.GREEN):
    global VERBOSE

    if VERBOSE:
        print(f"{color}{msg}{Style.RESET_ALL}")


def main():
    global VERBOSE

    args = parse_args()
    try:
        if args.verbose:
            VERBOSE = True
    except:
        pass

    if args.operation == "split":
        split_file(args.file, args.parts, args.chunk_size, args.remove)
    elif args.operation == "merge":
        merge(args.dir, args.remove)


if __name__ == "__main__":
    main()
