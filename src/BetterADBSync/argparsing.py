from typing import List, Optional
from dataclasses import dataclass
import argparse
from pathlib import Path

@dataclass
class Args():
    logging_no_color: bool
    logging_verbosity_verbose: int
    logging_verbosity_quiet: int

    dry_run: bool
    copy_links: bool
    exclude: List[str]
    exclude_from: List[Path]
    delete: bool
    delete_excluded: bool
    force: bool
    show_progress: bool
    adb_encoding: str

    adb_bin: str
    adb_flags: List[str]
    adb_options: List[List[str]]

    direction: str

    direction_push_local: Optional[str]
    direction_push_android: Optional[str]

    direction_pull_android: Optional[str]
    direction_pull_local: Optional[str]

def get_cli_args(docstring: str, version: str) -> Args:
    parser = argparse.ArgumentParser(description = docstring)
    parser.add_argument("--version",
        action = "version",
        version = version
    )

    parser_logging = parser.add_argument_group(title = "logging")
    parser_logging.add_argument("--no-color",
        help = "Disable colored logging (Linux only)",
        action = "store_true",
        dest = "logging_no_color"
    )
    parser_logging_verbosity = parser_logging.add_mutually_exclusive_group(required = False)
    parser_logging_verbosity.add_argument("-v", "--verbose",
        help = "Increase logging verbosity: -v for debug",
        action = "count",
        dest = "logging_verbosity_verbose",
        default = 0
    )
    parser_logging_verbosity.add_argument("-q", "--quiet",
        help = "Decrease logging verbosity: -q for warning, -qq for error, -qqq for critical, -qqqq for no logging messages",
        action = "count",
        dest = "logging_verbosity_quiet",
        default = 0
    )

    parser.add_argument("-n", "--dry-run",
        help = "Perform a dry run; do not actually copy and delete etc",
        action = "store_true",
        dest = "dry_run"
    )
    parser.add_argument("-L", "--copy-links",
        help = "Follow symlinks and copy their referent file / directory",
        action = "store_true",
        dest = "copy_links"
    )
    parser.add_argument("--exclude",
        help = "fnmatch pattern to ignore relative to source (reusable)",
        action = "append",
        dest = "exclude",
        default = []
    )
    parser.add_argument("--exclude-from",
        help = "Filename of file containing fnmatch patterns to ignore relative to source (reusable)",
        metavar = "EXCLUDE_FROM",
        type = Path,
        action = "append",
        dest = "exclude_from",
        default = []
    )
    parser.add_argument("--del",
        help = "Delete files at the destination that are not in the source",
        action = argparse.BooleanOptionalAction,
        default = True,
        dest = "delete"
    )
    parser.add_argument("--delete-excluded",
        help = "Delete files at the destination that are excluded",
        action = "store_true",
        dest = "delete_excluded"
    )
    parser.add_argument("--force",
        help = "Allows files to overwrite folders and folders to overwrite files. This is false by default to prevent large scale accidents",
        action = "store_true",
        dest = "force"
    )
    parser.add_argument("--show-progress",
        help = "Show progress from 'adb push' and 'adb pull' commands",
        action = "store_true",
        dest = "show_progress"
    )
    parser.add_argument("--adb-encoding",
        help = "Which encoding to use when talking to adb. Defaults to UTF-8. Relevant to GitHub issue #22",
        dest = "adb_encoding",
        default = "UTF-8"
    )

    parser_adb = parser.add_argument_group(title = "ADB arguments",
        description = "By default ADB works for me without touching any of these, but if you have any specific demands then go ahead. See 'adb --help' for a full list of adb flags and options"
    )
    parser_adb.add_argument("--adb-bin",
        help = "Use the given adb binary. Defaults to 'adb' ie whatever is on path",
        dest = "adb_bin",
        default = "adb")
    parser_adb.add_argument("--adb-flag",
        help = "Add a flag to call adb with, eg '--adb-flag d' for adb -d, that is return an error if more than one device is connected",
        metavar = "ADB_FLAG",
        action = "append",
        dest = "adb_flags",
        default = []
    )
    parser_adb.add_argument("--adb-option",
        help = "Add an option to call adb with, eg '--adb-option P 5037' for adb -P 5037, that is use port 5037 for the adb server",
        metavar = ("OPTION", "VALUE"),
        nargs = 2,
        action = "append",
        dest = "adb_options",
        default = []
    )

    parser_direction = parser.add_subparsers(title = "direction",
        dest = "direction",
        required = True
    )

    parser_direction_push = parser_direction.add_parser("push",
        help = "Push from computer to phone"
    )
    parser_direction_push.add_argument("direction_push_local",
        metavar = "LOCAL",
        help = "Local path"
    )
    parser_direction_push.add_argument("direction_push_android",
        metavar = "ANDROID",
        help = "Android path"
    )

    parser_direction_pull = parser_direction.add_parser("pull",
        help = "Pull from phone to computer"
    )
    parser_direction_pull.add_argument("direction_pull_android",
        metavar = "ANDROID",
        help = "Android path"
    )
    parser_direction_pull.add_argument("direction_pull_local",
        metavar = "LOCAL",
        help = "Local path"
    )

    args = parser.parse_args()

    if args.direction == "push":
        args_direction_ = (
            args.direction_push_local,
            args.direction_push_android,
            None,
            None
        )
    else:
        args_direction_ = (
            None,
            None,
            args.direction_pull_android,
            args.direction_pull_local
        )

    args = Args(
        args.logging_no_color,
        args.logging_verbosity_verbose,
        args.logging_verbosity_quiet,

        args.dry_run,
        args.copy_links,
        args.exclude,
        args.exclude_from,
        args.delete,
        args.delete_excluded,
        args.force,
        args.show_progress,
        args.adb_encoding,

        args.adb_bin,
        args.adb_flags,
        args.adb_options,

        args.direction,
        *args_direction_
    )

    return args
