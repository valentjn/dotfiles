#!/usr/bin/env python
# Copyright (C) 2025 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Check code quality using mypy and Ruff."""

import argparse
import logging
import subprocess
import sys

logger = logging.getLogger(__name__)


def main() -> None:
    """Run main function."""
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    arguments = parse_arguments()
    run_ruff_check(verbose=arguments.verbose)
    run_ruff_format(verbose=arguments.verbose)
    run_mypy(verbose=arguments.verbose)
    logger.info("all checks passed")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="check code quality")
    parser.add_argument("-v", "--verbose", action=argparse.BooleanOptionalAction, help="show more output")
    return parser.parse_args()


def run_ruff_format(*, verbose: bool = False) -> None:
    """Run ruff format."""
    command = ["uvx", "ruff", "format"]
    if not verbose:
        command.append("--quiet")
    run(command, program_name="ruff format")


def run_mypy(*, verbose: bool = False) -> None:
    """Run mypy."""
    command = ["uvx", "mypy", "--strict"]
    if verbose:
        command.append("--verbose")
    command.append(".")
    run(command)


def run_ruff_check(*, verbose: bool = False) -> None:
    """Run ruff check."""
    command = [
        "uvx",
        "ruff",
        "--quiet",
        "check",
        "--extend-select",
        "ALL",
        "--fix",
        "--ignore",
        ",".join(  # noqa: FLY002
            [
                # missing-trailing-comma
                "COM812",
                # incorrect-blank-line-before-class
                "D203",
                # multi-line-summary-second-line
                "D213",
                # suspicious-url-open-usage
                "S310",
                # subprocess-without-shell-equals-true
                "S603",
                # start-process-with-partial-path
                "S607",
            ],
        ),
        "--line-length",
        "120",
        "--output-format",
        "concise",
        "--target-version",
        "py313",
    ]
    if verbose:
        command.append("--show-files")
    run(command, program_name="ruff check")


def run(
    command: list[str],
    *,
    log: bool = True,
    program_name: str | None = None,
) -> None:
    """Run a command and exit if it fails."""
    if program_name is None:
        match command[0]:
            case "uvx":
                program_name = command[1]
            case _:
                program_name = command[0]
    if log:
        logger.info("running %s", program_name)
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exception:
        logger.error("%s failed with exit code %d", program_name, exception.returncode)  # noqa: TRY400
        sys.exit(exception.returncode)


if __name__ == "__main__":
    main()
