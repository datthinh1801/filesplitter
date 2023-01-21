"""Sync data with git
"""
import argparse

from pathlib import Path

import git


def parse_args():
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Backup a directory with git.")
    repo_group = parser.add_argument_group("repository")
    dir_group = repo_group.add_mutually_exclusive_group()
    dir_group.add_argument(
        "-d",
        "--dir",
        help="the directory that already has .git (default: current directory)",
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
        help="modes of commit (batch: commit all files at once;\
            individual: commit individual files separately) (default: individual)",
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
    """Push updates to the remote repository.

    Args:
        repo (git.Repo): the Repo object of the repository.
        remote_name (str): the name of the remote repository.
    """
    try:
        remote = repo.remote(remote_name)
        remote.push()
    except ValueError:
        print("Remote doesn't exist")


def fetch_updates(repo: git.Repo, remote_name: str):
    """Fetch updates from the remote repository.

    Args:
        repo (git.Repo): the Repo object of the repository.
        remote_name (str): the name of the remote repository.
    """
    try:
        remote = repo.remote(remote_name)
        remote.fetch()
    except ValueError:
        print("Remote doesn't exist")


def batch_commit(
    repo: git.Repo,
    msg: str,
    remote_name: str = "origin",
    fetch: bool = False,
    push: bool = False,
):
    """Commit (and push) untracked and modified files all at once.

    Args:
        repo (git.Repo): the Repo object of the repository.
        msg (str): the commit message.
        remote_name (str, optional): the name of the remote repository. Defaults to "origin".
        fetch (bool, optional): fetch updates before doing commit. Defaults to False.
        push (bool, optional): push updates after doing commit. Defaults to False.
    """
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
        try:
            push_updates(repo, remote_name)
        except KeyboardInterrupt:
            print("Keyboard interrupted! Exit...")


def individual_commit(
    repo: git.Repo,
    msg: str,
    remote_name: str = "origin",
    fetch: bool = False,
    push: bool = False,
):
    """Commit (and push) untracked and modified files individually.

    Args:
        repo (git.Repo): the Repo object of the repository.
        msg (str): the commit message.
        remote_name (str, optional): the name of the remote repository. Defaults to "origin".
        fetch (bool, optional): fetch updates before doing commit. Defaults to False.
        push (bool, optional): push updates after doing commit. Defaults to False.
    """
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
            try:
                push_updates(repo, remote_name)
            except KeyboardInterrupt:
                print("Keyboard interrupted! Exit...")
                break


def get_changed_and_untracked_files(repo: git.Repo):
    """Get untracked and modified files of the repository.

    Args:
        repo (git.Repo): the Repo object of the repository.
    """
    changed_files = [item.a_path for item in repo.index.diff(None)]
    untracked_files = repo.untracked_files
    to_commit_files = changed_files + untracked_files
    return to_commit_files


def create_new_remote(repo: git.Repo, remote_name: str, remote_url: str):
    """Create a new remote repository for the local repository.

    Args:
        repo (git.Repo): the Repo object of the local repository.
        remote_name (str): the name of the remote repository.
        remote_url (str): the URL of the remote repository.
    """
    repo.create_remote(remote_name, remote_url)


def main():
    """Main routine of git_sync."""
    args = parse_args()
    if args.bare:
        repo = git.Repo.init()
    else:
        repo = git.Repo(args.git_dir)

    if args.create_remote:
        create_new_remote(repo, args.remote_name, args.remote_url)

    if args.commit:
        if args.commit_mode == "batch":
            batch_commit(
                repo,
                args.commit_message,
                remote_name=args.remote_name,
                fetch=args.fetch,
                push=args.push,
            )
        elif args.commit_mode == "individual":
            individual_commit(
                repo,
                args.commit_message,
                remote_name=args.remote_name,
                fetch=args.fetch,
                push=args.push,
            )

    print("Finished!")


if __name__ == "__main__":
    main()
