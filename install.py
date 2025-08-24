#!/usr/bin/env python
# Copyright (C) 2025 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Install dotfiles in home directory."""

import argparse
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

START_DELIMITER = "valentjn_dotfiles_start"
END_DELIMITER = "valentjn_dotfiles_end"

logger = logging.getLogger(__name__)


def main() -> None:
    """Run main function."""
    logging.basicConfig(format="%(levelname)s %(message)s", level=logging.INFO)
    arguments = parse_arguments()
    install_text(".bashrc", dry_run=arguments.dry_run)
    install_text(".gitconfig", dry_run=arguments.dry_run)
    install_text_dir(".local/bin", dry_run=arguments.dry_run, overwrite=True)
    install_in_workspaces(
        install_json,
        ".vscode/settings.json",
        dry_run=arguments.dry_run,
    )


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="install dotfiles")
    parser.add_argument(
        "-n",
        "--dry-run",
        action=argparse.BooleanOptionalAction,
        help="show what would be done without making changes",
    )
    return parser.parse_args()


def install_in_workspaces(
    install: Callable[..., None],
    *args: Any,  # noqa: ANN401
    **kwargs: Any,  # noqa: ANN401
) -> None:
    """Install file in all workspaces."""
    for workspace in sorted(Path("/workspaces").iterdir()):
        if workspace.name != "dotfiles" and not workspace.name.startswith("."):
            install(*args, **kwargs, target_dir=workspace)


def install_json(
    path: Path | str,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    target_dir: Path | str | None = None,
) -> None:
    """Install patch into a JSON file."""
    start_delimiter = None if overwrite else f"// {START_DELIMITER}"
    end_delimiter = None if overwrite else f"// {END_DELIMITER}"
    source, target = get_source_and_target_paths(path, target_dir=target_dir)
    patch = source.read_text()
    start_brace, end_brace = get_braces(patch)
    string = target.read_text() if target.exists() else f"{start_brace}{end_brace}"
    if (
        start_delimiter is not None
        and end_delimiter is not None
        and start_delimiter not in string
    ):
        index = string.index(end_brace)
        string = (
            f"{string[:index]}\n{start_delimiter}\n{end_delimiter}\n{string[index:]}"
        )
    patch = patch[patch.index(start_brace) + 1 : patch.rindex(end_brace)]
    string = install_string(string, patch, start_delimiter, end_delimiter)
    write_file(source, string, target, dry_run=dry_run)


def get_braces(code: str) -> tuple[str, str]:
    """Get the type of braces or brackets used in JSON code."""
    brace_index = code.find("{")
    bracket_index = code.find("[")
    if brace_index == -1 and bracket_index == -1:
        msg = "no braces or brackets found"
        raise ValueError(msg)
    if brace_index == -1:
        return "[", "]"
    if bracket_index == -1:
        return "{", "}"
    if brace_index < bracket_index:
        return "{", "}"
    return "[", "]"


def install_text(
    path: Path | str,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    target_dir: Path | str | None = None,
) -> None:
    """Install patch into a text file (e.g., INI)."""
    start_delimiter = None if overwrite else f"# {START_DELIMITER}"
    end_delimiter = None if overwrite else f"# {END_DELIMITER}"
    source, target = get_source_and_target_paths(path, target_dir=target_dir)
    string = target.read_text() if target.exists() else ""
    string = install_string(string, source.read_text(), start_delimiter, end_delimiter)
    write_file(source, string, target, dry_run=dry_run)


def install_text_dir(
    path: Path | str,
    *,
    dry_run: bool = False,
    overwrite: bool = False,
    target_dir: Path | str | None = None,
) -> None:
    """Install all text files in a directory."""
    for file in sorted(Path(path).iterdir()):
        if file.is_file():
            install_text(
                file,
                dry_run=dry_run,
                overwrite=overwrite,
                target_dir=target_dir,
            )


def install_string(
    string: str,
    patch: str,
    start_delimiter: str | None,
    end_delimiter: str | None,
) -> str:
    """Install a patch into a string with delimiters."""
    if start_delimiter is None or end_delimiter is None:
        return patch
    patch_with_delimiters = f"\n{start_delimiter}\n{patch}\n{end_delimiter}\n"
    start_index = string.find(start_delimiter)
    end_index = string.find(end_delimiter, start_index)
    if start_index == -1 or end_index == -1:
        return f"{string}{patch_with_delimiters}"
    return f"{string[: start_index - 1]}{patch_with_delimiters}{string[end_index + len(end_delimiter) + 1 :]}"


def get_source_and_target_paths(
    path: Path | str,
    target_dir: Path | str | None = None,
) -> tuple[Path, Path]:
    """Get source and target paths for a given file."""
    if target_dir is None:
        target_dir = Path.home()
    root = Path(__file__).parent
    path = Path(path)
    if path.is_absolute():
        path = path.relative_to(root)
    source = root / path
    target = target_dir / path
    return source, target


def write_file(
    source: Path | str,
    string: str,
    target: Path | str,
    *,
    dry_run: bool = False,
) -> None:
    """Write a string to a file."""
    source, target = Path(source), Path(target)
    if dry_run:
        logger.info("would write %s:", target)
        logger.info(string)
        return
    logger.info("writing %s", target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(string, encoding="utf-8")
    target.chmod(source.stat().st_mode)


if __name__ == "__main__":
    main()
