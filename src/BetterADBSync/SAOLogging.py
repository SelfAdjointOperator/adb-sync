"""Nice logging, with colors on Linux."""

from typing import Any, Union
import logging
import sys

class ColoredFormatter(logging.Formatter):
    """Logging Formatter to add colors"""

    fg_bright_blue    = "\x1b[94m"
    fg_yellow        = "\x1b[33m"
    fg_red           = "\x1b[31m"
    fg_bright_red_bold = "\x1b[91;1m"
    reset            = "\x1b[0m"

    def __init__(self, fmt, datefmt):
        super().__init__()
        self.messagefmt = fmt
        self.datefmt = datefmt

        self.formats = {
            logging.DEBUG:    "{}{}{}".format(self.fg_bright_blue, self.messagefmt, self.reset),
            logging.INFO:       "{}".format(self.messagefmt),
            logging.WARNING:  "{}{}{}".format(self.fg_yellow, self.messagefmt, self.reset),
            logging.ERROR:    "{}{}{}".format(self.fg_red, self.messagefmt, self.reset),
            logging.CRITICAL: "{}{}{}".format(self.fg_bright_red_bold, self.messagefmt, self.reset)
        }

        self.formatters = {
            logging.DEBUG:    logging.Formatter(self.formats[logging.DEBUG],    datefmt = self.datefmt),
            logging.INFO:     logging.Formatter(self.formats[logging.INFO],     datefmt = self.datefmt),
            logging.WARNING:  logging.Formatter(self.formats[logging.WARNING],  datefmt = self.datefmt),
            logging.ERROR:    logging.Formatter(self.formats[logging.ERROR],    datefmt = self.datefmt),
            logging.CRITICAL: logging.Formatter(self.formats[logging.CRITICAL], datefmt = self.datefmt)
        }

    def format(self, record):
        formatter = self.formatters[record.levelno]
        return formatter.format(record)

def setup_root_logger(
        no_color: bool = False,
        verbosity_level: int = 0,
        quietness_level: int = 0,
        messagefmt: str = "[%(asctime)s][%(levelname)s] %(message)s (%(filename)s:%(lineno)d)",
        messagefmt_verbose: str = "[%(asctime)s][%(levelname)s] %(message)s (%(filename)s:%(lineno)d)",
        datefmt: str = "%Y-%m-%d %H:%M:%S"
    ):
    messagefmt_to_use = messagefmt_verbose if verbosity_level else messagefmt
    logging_level = 10 * (2 + quietness_level - verbosity_level)
    if not no_color and sys.platform == "linux":
        formatter_class = ColoredFormatter
    else:
        formatter_class = logging.Formatter

    root_logger = logging.getLogger()
    root_logger.setLevel(logging_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter_class(fmt = messagefmt_to_use, datefmt = datefmt))
    root_logger.addHandler(console_handler)

def logging_fatal(message, log_stack_info: bool = True, exit_code: int = 1, force_exit: bool = False):
    # TODO collect all fatal errors, and show all of it when program terminated. Useful for tracking files that has problems.
    logging.critical(message)
    logging.debug("Stack Trace", stack_info = log_stack_info)
    if force_exit:
        logging.critical("Exiting")
        raise SystemExit(exit_code)

def log_tree(title, tree, finals = None, log_leaves_types = True, logging_level = logging.INFO):
    """Log tree nicely if it is a dictionary.
    log_leaves_types can be False to log no leaves, True to log all leaves, or a tuple of types for which to log."""
    if finals is None:
        finals = []
    if not isinstance(tree, dict):
        logging.log(msg = "{}{}{}".format(
            "".join([" " if final else "│" for final in finals[:-1]] + ["└" if final else "├" for final in finals[-1:]]),
            title,
            ": {}".format(tree) if log_leaves_types is not False and (log_leaves_types is True or isinstance(tree, log_leaves_types)) else ""
        ), level = logging_level)
    else:
        logging.log(msg = "{}{}".format(
            "".join([" " if final else "│" for final in finals[:-1]] + ["└" if final else "├" for final in finals[-1:]]),
            title
        ), level = logging_level)
        tree_items = list(tree.items())
        for key, value in tree_items[:-1]:
            log_tree(key, value, finals = finals + [False], log_leaves_types = log_leaves_types, logging_level = logging_level)
        for key, value in tree_items[-1:]:
            log_tree(key, value, finals = finals + [True], log_leaves_types = log_leaves_types, logging_level = logging_level)

# like logging.CRITICAl, logging.DEBUG etc
FATAL = 60

def perror(s: Union[str, Any], e: Exception, logging_level: int = logging.ERROR):
    strerror = e.strerror if (isinstance(e, OSError) and e.strerror is not None) else e.__class__.__name__
    msg = f"{s}{': ' if s else ''}{strerror}"
    if logging_level == FATAL:
        logging_fatal(msg, force_exit = True)
    else:
        logging.log(logging_level, msg)
