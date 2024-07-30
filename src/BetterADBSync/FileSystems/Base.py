from __future__ import annotations
from typing import Iterable, List, Tuple, Union
import logging
import os
import stat

from ..SAOLogging import perror

class FileSystem():
    def __init__(self, adb_arguments: List[str]) -> None:
        self.adb_arguments = adb_arguments
        self.has_invalid_name_potential = False

    def _get_files_tree(self, tree_path: str, tree_path_stat: os.stat_result, follow_links: bool = False):
        # the reason to have two functions instead of one purely recursive one is to use self.lstat_in_dir ie ls
        # which is much faster than individually stat-ing each file. Hence we have get_files_tree's special first lstat
        if stat.S_ISLNK(tree_path_stat.st_mode):
            if not follow_links:
                logging.warning(f"Ignoring symlink {tree_path}")
                return None
            logging.debug(f"Following symlink {tree_path}")
            try:
                tree_path_realpath = self.realpath(tree_path)
                tree_path_stat_realpath = self.lstat(tree_path_realpath)
            except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
                perror(f"Skipping symlink {tree_path}", e)
                return None
            return self._get_files_tree(tree_path_realpath, tree_path_stat_realpath, follow_links = follow_links)
        elif stat.S_ISDIR(tree_path_stat.st_mode):
            tree = {".": (60 * (int(tree_path_stat.st_atime) // 60), 60 * (int(tree_path_stat.st_mtime) // 60))}
            for filename, stat_object_child, in self.lstat_in_dir(tree_path):
                if filename in [".", ".."]:
                    continue
                tree[filename] = self._get_files_tree(
                    self.join(tree_path, filename),
                    stat_object_child,
                    follow_links = follow_links)
            return tree
        elif stat.S_ISREG(tree_path_stat.st_mode):
            return (60 * (int(tree_path_stat.st_atime) // 60), 60 * (int(tree_path_stat.st_mtime) // 60)) # minute resolution
        else:
            raise NotImplementedError

    def get_files_tree(self, tree_path: str, follow_links: bool = False):
        statObject = self.lstat(tree_path)
        return self._get_files_tree(tree_path, statObject, follow_links = follow_links)

    def remove_tree(self, tree_path: str, tree: Union[Tuple[int, int], dict], dry_run: bool = True) -> None:
        if isinstance(tree, tuple):
            logging.info(f"Removing {tree_path}")
            if not dry_run:
                self.unlink(tree_path)
        elif isinstance(tree, dict):
            remove_folder = tree.pop(".", False)
            for key, value in tree.items():
                self.remove_tree(self.normpath(self.join(tree_path, key)), value, dry_run = dry_run)
            if remove_folder:
                logging.info(f"Removing folder {tree_path}")
                if not dry_run:
                    self.rmdir(tree_path)
        else:
            raise NotImplementedError

    def push_tree_here(self,
        tree_path: str,
        relative_tree_path: str, # for logging paths of files / folders copied relative to the source root / destination root
                                 # nicely instead of repeating the root every time; rsync does this nice logging
        tree: Union[Tuple[int, int], dict],
        destination_root: str,
        fs_source: FileSystem,
        fs_destination: FileSystem,
        dry_run: bool = True,
        show_progress: bool = False
        ) -> None:
        if isinstance(tree, tuple):
            if dry_run:
                logging.info(f"{relative_tree_path}")
            else:
                if not show_progress:
                    # log this instead of letting adb display output
                    logging.info(f"{relative_tree_path}")
                self.push_file_here(tree_path, destination_root, show_progress = show_progress)
                self.utime(destination_root, tree)
        elif isinstance(tree, dict):
            try:
                tree.pop(".") # directory needs making
                logging.info(f"{relative_tree_path}{self.sep}")
                if not dry_run:
                    self.makedirs(destination_root)
            except KeyError:
                pass
            for key, value in tree.items():
                # FIXME sync will work improperly if file with name converted already exist
                destination_key: str = fs_destination.convert_invalid_file_name(key)    # might not need when copy a file, or folder with 1-layer deep
                if key != destination_key:
                    logging.info(f"convert {key} -> {destination_key}")
                self.push_tree_here(
                    fs_source.normpath(fs_source.join(tree_path, key)),
                    fs_source.join(relative_tree_path, key),
                    value,
                    self.normpath(self.join(destination_root, destination_key)),
                    fs_source,
                    fs_destination,
                    dry_run = dry_run,
                    show_progress = show_progress
                )
        else:
            raise NotImplementedError

    # Abstract methods below implemented in Local.py and Android.py

    @property
    def sep(self) -> str:
        raise NotImplementedError

    def unlink(self, path: str) -> None:
        raise NotImplementedError

    def rmdir(self, path: str) -> None:
        raise NotImplementedError

    def makedirs(self, path: str) -> None:
        raise NotImplementedError

    def realpath(self, path: str) -> str:
        raise NotImplementedError

    def lstat(self, path: str) -> os.stat_result:
        raise NotImplementedError

    def lstat_in_dir(self, path: str) -> Iterable[Tuple[str, os.stat_result]]:
        raise NotImplementedError

    def utime(self, path: str, times: Tuple[int, int]) -> None:
        raise NotImplementedError

    def join(self, base: str, leaf: str) -> str:
        raise NotImplementedError

    def split(self, path: str) -> Tuple[str, str]:
        raise NotImplementedError

    def normpath(self, path: str) -> str:
        raise NotImplementedError

    def push_file_here(self, source: str, destination: str, show_progress: bool = False) -> None:
        raise NotImplementedError

    def convert_invalid_file_name(self, path_destination: str) -> str:
        raise NotImplementedError  # Problem only persist on Windows. No implement for other system

    def validate_args_path(self, path: str) -> str:
        raise NotImplementedError
