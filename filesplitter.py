"""
Split a large file into smaller files. Or merge smaller files into the original large file.
"""
import argparse
import hashlib
import math
import zlib

from pathlib import Path
from configparser import ConfigParser
from colorama import Fore, Style


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        argparse.Namespace: a Namespace object including all arguments' value.
    """
    parser = argparse.ArgumentParser(
        description="Split a large file into smaller files (split in parts or chunk size)\
            or merge file parts into the large file.",
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
        help="the max size (in bytes) of each small file to split into",
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
    split_parser.add_argument(
        "--compress",
        help="compress the splitted files",
        dest="compress",
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
    filename: str or Path,
    parts: int = 0,
    chunk_size: int = 0,
    remove: bool = False,
    compress: bool = False,
):
    """Split a file into smaller files (into parts or into files or chunk_size).

    Args:
        filename (str or Path): the filename or the Path object of the file to split.
        parts (int, optional): the number of parts to split into. Defaults to 0.
        chunk_size (int, optional): the chunk_size of smaller files to split into. Defaults to 0.
        remove (bool, optional): remove the original file after splitting. Defaults to False.
    """
    if parts == 0 and chunk_size == 0:
        verbose("[x] Parts and chunk size cannot both be 0!", Fore.RED)
        return

    filepath = (Path(".") / filename).resolve()
    filename = filepath.name
    basename = filename.removesuffix("".join(filepath.suffixes))
    filesize = filepath.stat().st_size

    config = ConfigParser()
    config["ORIGINAL"] = {"filename": filename, "size": filesize}

    verbose(f"[+] Source file: {filepath}")
    verbose(f"[+] File size: {filesize}")
    verbose("[i] Calculating file hash")
    filehash = compute_hash(filepath)
    verbose(f"[i] File hash: {filehash}", Fore.YELLOW)

    config["ORIGINAL"]["hash"] = filehash
    config["OPERATION"] = {"compress": compress}

    if parts > 0:
        chunk_size = math.ceil(filesize / parts)
    else:
        parts = math.ceil(filesize / chunk_size)

    verbose(f"[+] Parts: {parts}")
    verbose(f"[+] Segment size: {chunk_size}")

    config["PARTS"] = {"parts": parts}

    verbose(f"[i] Creating {basename} directory", Fore.YELLOW)
    subdir = filepath.parent / basename
    remove_dir(subdir)
    subdir.mkdir()

    verbose("[i] Splitting files")
    bytes_write = 0
    with filepath.open("rb") as file_handle:
        for part in range(parts):
            chunk = file_handle.read(chunk_size)
            if compress:
                chunk = zlib.compress(chunk)

            part_filepath = subdir / f"{filename}.{part}.prt"
            verbose(f"[i] Writing to file: {part_filepath.name}")
            with part_filepath.open("wb") as filepath_handle:
                filepath_handle.write(chunk)
                bytes_write += len(chunk)

            config["PARTS"][str(part)] = part_filepath.name

    verbose(f"[+] {bytes_write} bytes written", Fore.GREEN)
    verbose("[i] Writing configuration")
    with (subdir / "config.ini").open("w", encoding="utf8") as config_file:
        config.write(config_file)

    if remove:
        verbose("[i] Removing the original file")
        filepath.unlink(missing_ok=True)
    verbose("[+] Finish!", Fore.GREEN)


def merge(dirname: str or Path, remove: bool = False):
    """Merge files within a directory into the original large file.

    Args:
        dirname (str or Path): directory name of the Path object of the directory.
        remove (bool, optional): remove all smaller files and \
            the directory after merging. Defaults to False.
    """
    if isinstance(dirname, Path) and dirname.is_absolute():
        dirpath = dirname
    else:
        dirpath = Path(".") / dirname
    verbose(f"[i] Reading directory: {dirpath.resolve()}", Fore.YELLOW)
    if not dirpath.is_dir():
        verbose("[x] Directory not exists!", Fore.RED)
        return

    verbose("[i] Reading configuration file")
    config = ConfigParser()
    config.read(dirpath / "config.ini", encoding="utf8")
    filename = config["ORIGINAL"]["filename"]
    filepath = dirpath.parent / filename
    if filepath.is_file():
        filepath.unlink()

    verbose("[i] Merging files")
    decompress = config["OPERATION"]["compress"]
    for path in get_sorted_files(dirpath, config):
        verbose(f"[i] Reading file: {path.name}")
        buffer = path.read_bytes()
        if decompress:
            buffer = zlib.decompress(buffer)
        with filepath.open("ab") as file_handle:
            file_handle.write(buffer)

    # check if the file has contents
    if not filepath.is_file():
        filepath.write_bytes(b"")

    verbose("[i] Verifying file hash")
    ver_filehash = compute_hash(filepath)
    filehash = config["ORIGINAL"]["hash"]
    if ver_filehash == filehash:
        verbose("[+] Hash verification succeeded!", Fore.GREEN)
    else:
        verbose("[x] Hash verification failed!", Fore.RED)
        exit(1)

    if remove:
        verbose("[i] Removing the directory")
        remove_dir(dirpath)
    verbose("[+] Finish!", Fore.GREEN)


def compute_hash(filepath: Path, block_size: int = 512) -> str:
    """Compute hash for a filepath efficiently.

    Args:
        filepath (Path): the Path object of the file.
        block_size (int, optional): the size of the block to read per time.

    Returns:
        (str): the hex digest of the file.
    """
    sha256 = hashlib.sha256()
    with filepath.open("rb") as file_handle:
        while True:
            buffer = file_handle.read(block_size)
            if not buffer:
                break
            sha256.update(buffer)
    return sha256.hexdigest()


def remove_dir(dirpath: Path):
    """Remove the given directory.

    Args:
        dirpath (Path): the Path object of the directory.
    """
    if dirpath.is_dir():
        for path in dirpath.glob("*"):
            path.unlink()
        dirpath.rmdir()


def get_sorted_files(dirpath: Path, config: ConfigParser):
    """Return files within a directory in a sorted order based on their part number.

    Args:
        dirpath (Path): the Path object of the directory.
    """
    parts = int(config["PARTS"]["parts"])
    filepaths = []
    for part in range(parts):
        filename = config["PARTS"][str(part)]
        filepath = dirpath / filename
        filepaths.append(filepath)
    return filepaths


def verbose(msg: str, color=Fore.RESET):
    """Print a message with color.

    Args:
        msg (str): the message to print.
        color (optional): the color of the message to print. Defaults to Fore.GREEN.
    """
    print(f"{color}{msg}{Style.RESET_ALL}")


def main():
    """The main routine of filesplitter."""
    args = parse_args()
    if args.operation == "split":
        split_file(args.file, args.parts, args.chunk_size, args.remove, args.compress)
    elif args.operation == "merge":
        merge(args.dir, args.remove)


if __name__ == "__main__":
    main()
