import argparse
import git
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(description="Backup a directory with git.")
    repo_group = parser.add_argument_group("repository")
    dir_group = repo_group.add_mutually_exclusive_group()
    dir_group.add_argument(
        "-d",
        "--dir",
        help="the directory that already has .git",
        dest="git_dir",
        default=".",
        type=str,
    )
    dir_group.add_argument(
        "-b",
        "--bare",
        help="initialize a bare repository",
        dest="bare",
        action="store_true",
    )
    repo_group.add_argument(
        "--push", help="perform push operation", dest="push", action="store_true"
    )
    repo_group.add_argument(
        "--fetch", help="perform fetch operation", dest="fetch", action="store_true"
    )

    commit_group = parser.add_argument_group("commit")
    commit_group.add_argument(
        "--commit", help="do commit", dest="commit", action="store_true"
    )
    commit_group.add_argument(
        "--mode",
        help="modes of commit (batch: commit all files at once; individual: commit individual files separately) (default: individual)",
        choices=["batch", "individual"],
        default="individual",
        dest="commit_mode",
        type=str,
    )
    commit_group.add_argument(
        "-m", "--message", help="commit message", dest="commit_message", type=str
    )

    remote_group = parser.add_argument_group("remote")
    remote_group.add_argument(
        "--create-remote",
        help="create a new remote",
        dest="create_remote",
        action="store_true",
    )
    remote_group.add_argument(
        "--remote-url",
        help="the URL to create a new remote",
        dest="remote_url",
        type=str,
    )
    remote_group.add_argument(
        "--remote-name",
        help="the remote repository's name (default: origin)",
        dest="remote_name",
        default="origin",
    )

    return parser.parse_args()


def push_updates(repo: git.Repo, remote_name: str):
    try:
        remote = repo.remote(remote_name)
        remote.push()
    except ValueError:
        print("Remote doesn't exist")


def fetch_updates(repo: git.Repo, remote_name: str):
    try:
        remote = repo.remote(remote_name)
        remote.fetch()
    except ValueError:
        print("Remote doesn't exist")


def batch_commit(
    repo: git.Repo,
    git_dir: Path,
    msg: str,
    remote_name: str = "origin",
    fetch: bool = False,
    push: bool = False,
):
    if fetch:
        print("Fetching updates")
        fetch_updates(repo, remote_name)

    for path in get_changed_and_untracked_files(repo):
        if path.name == ".git":
            continue

        filepath = Path(path)
        print(f"Adding {filepath.name}")
        repo.index.add(filepath)
    repo.index.commit(msg)
    if push:
        print("Pushing updates")
        push_updates(repo, remote_name)


def individual_commit(
    repo: git.Repo,
    git_dir: Path,
    msg: str,
    remote_name: str = "origin",
    fetch: bool = False,
    push: bool = False,
):
    if fetch:
        print("Fetching updates")
        fetch_updates(repo, remote_name)

    for path in get_changed_and_untracked_files(repo):
        filepath = Path(path)
        print(f"Adding {filepath.name}")
        repo.index.add(filepath)
        repo.index.commit(msg)
        if push:
            print(f"Pushing {filepath.name}")
            push_updates(repo, remote_name)


def get_changed_and_untracked_files(repo: git.Repo):
    changed_files = [item.a_path for item in repo.index.diff(None)]
    untracked_files = repo.untracked_files
    to_commit_files = changed_files + untracked_files
    return to_commit_files


def create_new_remote(repo: git.Repo, remote_name: str, remote_url: str):
    repo.create_remote(remote_name, remote_url)


if __name__ == "__main__":
    args = parse_args()
    if args.bare:
        repo = git.Repo.init()
        git_dir = Path(".")
    else:
        repo = git.Repo(args.git_dir)
        git_dir = Path(args.git_dir)

    if args.create_remote:
        create_new_remote(repo, args.remote_name, args.remote_url)

    if args.commit:
        if args.commit_mode == "batch":
            batch_commit(
                repo,
                git_dir,
                args.commit_message,
                remote_name=args.remote_name,
                fetch=args.fetch,
                push=args.push,
            )
        elif args.commit_mode == "individual":
            individual_commit(
                repo,
                git_dir,
                args.commit_message,
                remote_name=args.remote_name,
                fetch=args.fetch,
                push=args.push,
            )

    print("Finished!")
