#!/usr/bin/env python
# Copyright (C) 2025 Julian Valentin
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Install dotfiles in home directory."""

import argparse
import json
import logging
import os
import shutil
import subprocess
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

START_DELIMITER = "valentjn_dotfiles_start"
END_DELIMITER = "valentjn_dotfiles_end"
IGNORE_START_DELIMITER = "valentjn_dotfiles_ignore_start"
IGNORE_END_DELIMITER = "valentjn_dotfiles_ignore_end"

logger = logging.getLogger(__name__)


def main() -> None:
    """Run main function."""
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    arguments = parse_arguments()
    install_text(".bashrc", dry_run=arguments.dry_run)
    install_text(".gitconfig", dry_run=arguments.dry_run)
    install_text_dir(".local/bin", dry_run=arguments.dry_run, overwrite=True)
    install_in_workspaces(
        install_json,
        ".vscode/settings.json",
        dry_run=arguments.dry_run,
    )
    install_uv()


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
    target_dir: Path | str | None = None,
) -> None:
    """Install patch into a JSON file."""
    source, target = get_source_and_target_paths(path, target_dir=target_dir)
    patch = read_source_file(source)
    target_str = json.dumps(merge_json(json.loads(patch), json.loads(target.read_text()))) if target.exists() else patch
    write_file(source, target_str, target, dry_run=dry_run)


def merge_json[T](source: T, target: T) -> T:
    """Merge two JSON arrays or objects."""
    if isinstance(source, dict):
        if not isinstance(target, dict):
            msg = "cannot merge JSON objects with non-objects"
            raise TypeError(msg)
        result = cast("T", source.copy())
        for key, value in target.items():
            result[key] = merge_json(source[key], value) if key in source else value  # type: ignore[index]
        return result
    if isinstance(source, list):
        if not isinstance(target, list):
            msg = "cannot merge JSON arrays with non-arrays"
            raise TypeError(msg)
        source_set = set(source)
        return cast("T", source + [item for item in target if item not in source_set])
    return source


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
    target_str = target.read_text() if target.exists() else ""
    target_str = install_string(read_source_file(source), target_str, start_delimiter, end_delimiter)
    write_file(source, target_str, target, dry_run=dry_run)


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
    patch: str,
    string: str,
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


def read_source_file(path: Path | str) -> str:
    """Read a source file."""
    string = Path(path).read_text(encoding="utf-8")
    lines = []
    in_ignored_section = False
    for line in string.splitlines():
        if IGNORE_START_DELIMITER in line:
            in_ignored_section = True
        if not in_ignored_section:
            lines.append(line)
        if IGNORE_END_DELIMITER in line:
            in_ignored_section = False
    return "\n".join(lines) + "\n"


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


def install_uv() -> None:
    """Install uv."""
    if shutil.which("uv") is None:
        logger.info("installing uv")
        url = "https://astral.sh/uv/install.sh"
        with urllib.request.urlopen(url) as response:
            install_script = response.read().decode("utf-8")
        subprocess.run(["sh", "-c", install_script], check=True, env={**os.environ, "UV_PRINT_QUIET": "1"})


if __name__ == "__main__":
    main()
