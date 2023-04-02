from typing import Iterable, Iterator, List, NoReturn, Tuple
import logging
import os
import re
import stat
import datetime
import subprocess

from ..SAOLogging import logging_fatal

from .Base import FileSystem

class AndroidFileSystem(FileSystem):
    RE_TESTCONNECTION_NO_DEVICE = re.compile("^adb\\: no devices/emulators found$")
    RE_TESTCONNECTION_DAEMON_NOT_RUNNING = re.compile("^\\* daemon not running; starting now at tcp:\\d+$")
    RE_TESTCONNECTION_DAEMON_STARTED = re.compile("^\\* daemon started successfully$")

    RE_LS_TO_STAT = re.compile(
        r"""^
        (?:
        (?P<S_IFREG> -) |
        (?P<S_IFBLK> b) |
        (?P<S_IFCHR> c) |
        (?P<S_IFDIR> d) |
        (?P<S_IFLNK> l) |
        (?P<S_IFIFO> p) |
        (?P<S_IFSOCK> s))
        [-r][-w][-xsS]
        [-r][-w][-xsS]
        [-r][-w][-xtT] # Mode string
        [ ]+
        (?:
        [0-9]+ # Number of hard links
        [ ]+
        )?
        [^ ]+ # User name/ID
        [ ]+
        [^ ]+ # Group name/ID
        [ ]+
        (?(S_IFBLK) [^ ]+[ ]+[^ ]+[ ]+) # Device numbers
        (?(S_IFCHR) [^ ]+[ ]+[^ ]+[ ]+) # Device numbers
        (?(S_IFDIR) (?P<dirsize>[0-9]+ [ ]+))? # Directory size
        (?(S_IFREG) (?P<st_size> [0-9]+) [ ]+) # Size
        (?(S_IFLNK) ([0-9]+) [ ]+) # Link length
        (?P<st_mtime>
        [0-9]{4}-[0-9]{2}-[0-9]{2} # Date
        [ ]
        [0-9]{2}:[0-9]{2}) # Time
        [ ]
        # Don't capture filename for symlinks (ambiguous).
        (?(S_IFLNK) .* | (?P<filename> .*))
        $""", re.DOTALL | re.VERBOSE)

    RE_NO_SUCH_FILE = re.compile("^.*: No such file or directory$")
    RE_LS_NOT_A_DIRECTORY = re.compile("ls: .*: Not a directory$")
    RE_TOTAL = re.compile("^total \\d+$")

    RE_REALPATH_NO_SUCH_FILE = re.compile("^realpath: .*: No such file or directory$")
    RE_REALPATH_NOT_A_DIRECTORY = re.compile("^realpath: .*: Not a directory$")

    ESCAPE_PATH_REPLACEMENTS = [
        [" ", "\\ "],
        ["'", "\\'"],
        ["(", "\\("],
        [")", "\\)"],
        ["!", "\\!"],
        ["&", "\\&"]
    ]

    ADBSYNC_END_OF_COMMAND = "ADBSYNC END OF COMMAND"

    def __init__(self, adb_arguments: List[str]) -> None:
        super().__init__(adb_arguments)
        self.proc_adb_shell = subprocess.Popen(
            self.adb_arguments + ["shell"],
            stdin = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT
        )

    def __del__(self):
        self.proc_adb_shell.stdin.close()
        self.proc_adb_shell.wait()

    def adb_shell(self, commands: List[str]) -> Iterator[str]:
        self.proc_adb_shell.stdin.write(" ".join(commands).encode())
        self.proc_adb_shell.stdin.write("\n".encode())
        self.proc_adb_shell.stdin.write(f"echo \"{self.ADBSYNC_END_OF_COMMAND}\"\n".encode())
        self.proc_adb_shell.stdin.flush()

        lines_to_yield: List[str] = []
        while adb_line := self.proc_adb_shell.stdout.readline():
            adb_line = adb_line.decode('ISO-8859-1').rstrip("\r\n")
            if adb_line == self.ADBSYNC_END_OF_COMMAND:
                break
            else:
                lines_to_yield.append(adb_line)
        for line in lines_to_yield:
            yield line

    def line_not_captured(self, line: str) -> NoReturn:
        logging.critical("ADB line not captured")
        logging_fatal(line)

    def escape_path(self, path: str) -> str:
        for replacement in self.ESCAPE_PATH_REPLACEMENTS:
            path = path.replace(*replacement)
        return path

    def test_connection(self):
        for line in self.adb_shell([":"]):
            print(line)

            if self.RE_TESTCONNECTION_DAEMON_NOT_RUNNING.fullmatch(line) or self.RE_TESTCONNECTION_DAEMON_STARTED.fullmatch(line):
                continue

            raise BrokenPipeError

    def ls_to_stat(self, line: str) -> Tuple[str, os.stat_result]:
        if self.RE_NO_SUCH_FILE.fullmatch(line):
            raise FileNotFoundError
        elif self.RE_LS_NOT_A_DIRECTORY.fullmatch(line):
            raise NotADirectoryError
        elif match := self.RE_LS_TO_STAT.fullmatch(line):
            match_groupdict = match.groupdict()
            st_mode = stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH # 755
            if match_groupdict['S_IFREG']:
                st_mode |= stat.S_IFREG
            if match_groupdict['S_IFBLK']:
                st_mode |= stat.S_IFBLK
            if match_groupdict['S_IFCHR']:
                st_mode |= stat.S_IFCHR
            if match_groupdict['S_IFDIR']:
                st_mode |= stat.S_IFDIR
            if match_groupdict['S_IFIFO']:
                st_mode |= stat.S_IFIFO
            if match_groupdict['S_IFLNK']:
                st_mode |= stat.S_IFLNK
            if match_groupdict['S_IFSOCK']:
                st_mode |= stat.S_IFSOCK
            st_size = None if match_groupdict["st_size"] is None else int(match_groupdict["st_size"])
            st_mtime = int(datetime.datetime.strptime(match_groupdict["st_mtime"], "%Y-%m-%d %H:%M").timestamp())

            # Fill the rest with dummy values.
            st_ino = 1
            st_rdev = 0
            st_nlink = 1
            st_uid = -2  # Nobody.
            st_gid = -2  # Nobody.
            st_atime = st_ctime = st_mtime

            return match_groupdict["filename"], os.stat_result((st_mode, st_ino, st_rdev, st_nlink, st_uid, st_gid, st_size, st_atime, st_mtime, st_ctime))
        else:
            self.line_not_captured(line)

    @property
    def sep(self) -> str:
        return "/"

    def unlink(self, path: str) -> None:
        for line in self.adb_shell(["rm", self.escape_path(path)]):
            self.line_not_captured(line)

    def rmdir(self, path: str) -> None:
        for line in self.adb_shell(["rm", "-r", self.escape_path(path)]):
            self.line_not_captured(line)

    def makedirs(self, path: str) -> None:
        for line in self.adb_shell(["mkdir", "-p", self.escape_path(path)]):
            self.line_not_captured(line)

    def realpath(self, path: str) -> str:
        for line in self.adb_shell(["realpath", self.escape_path(path)]):
            if self.RE_REALPATH_NO_SUCH_FILE.fullmatch(line):
                raise FileNotFoundError
            elif self.RE_REALPATH_NOT_A_DIRECTORY.fullmatch(line):
                raise NotADirectoryError
            else:
                return line
            # permission error possible?

    def lstat(self, path: str) -> os.stat_result:
        for line in self.adb_shell(["ls", "-lad", self.escape_path(path)]):
            return self.ls_to_stat(line)[1]

    def lstat_in_dir(self, path: str) -> Iterable[Tuple[str, os.stat_result]]:
        for line in self.adb_shell(["ls", "-la", self.escape_path(path)]):
            if self.RE_TOTAL.fullmatch(line):
                continue
            else:
                yield self.ls_to_stat(line)

    def utime(self, path: str, times: Tuple[int, int]) -> None:
        atime = datetime.datetime.utcfromtimestamp(times[0]).strftime("%Y%m%d%H%M")
        mtime = datetime.datetime.utcfromtimestamp(times[1]).strftime("%Y%m%d%H%M")
        for line in self.adb_shell(["touch", "-at", atime, "-mt", mtime, self.escape_path(path)]):
            self.line_not_captured(line)

    def join(self, base: str, leaf: str) -> str:
        return os.path.join(base, leaf).replace("\\", "/") # for Windows

    def split(self, path: str) -> Tuple[str, str]:
        head, tail = os.path.split(path)
        return head.replace("\\", "/"), tail # for Windows

    def normpath(self, path: str) -> str:
        return os.path.normpath(path).replace("\\", "/")

    def push_file_here(self, source: str, destination: str, show_progress: bool = False) -> None:
        if show_progress:
            kwargs_call = {}
        else:
            kwargs_call = {
                "stdout": subprocess.DEVNULL,
                "stderr": subprocess.DEVNULL
            }
        if subprocess.call(self.adb_arguments + ["push", source, destination], **kwargs_call):
            logging_fatal("Non-zero exit code from adb push")
