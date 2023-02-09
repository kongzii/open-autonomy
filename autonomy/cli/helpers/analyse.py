# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2023 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""Helpers for analyse command"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, cast

import click
from aea.components.base import load_aea_package
from aea.configurations.constants import DEFAULT_SKILL_CONFIG_FILE
from aea.configurations.data_types import PackageType
from aea.configurations.loader import load_configuration_object
from aea.package_manager.v1 import PackageManagerV1

from autonomy.analyse.dialogues import check_dialogues_in_a_skill_package
from autonomy.analyse.logs.base import (
    ENTER_ROUND_REGEX,
    EXIT_ROUND_REGEX,
    LOGS_DB,
    LogRow,
    TIME_FORMAT,
)
from autonomy.analyse.logs.collection import FromDirectory, LogCollection
from autonomy.analyse.logs.db import AgentLogsDB
from autonomy.cli.utils.click_utils import sys_path_patch


def load_package_tree(packages_dir: Path) -> None:
    """Load package tree."""

    pm = PackageManagerV1.from_dir(packages_dir=packages_dir)

    for package_id in pm.iter_dependency_tree():
        if package_id.package_type in (PackageType.AGENT, PackageType.SERVICE):
            continue

        package_path = pm.package_path_from_package_id(package_id=package_id)
        config_obj = load_configuration_object(
            package_type=package_id.package_type, directory=package_path
        )
        config_obj.directory = package_path
        load_aea_package(configuration=config_obj)


def list_all_skill_yaml_files(registry_path: Path) -> List[Path]:
    """List all skill yaml files in a local registry"""
    return sorted(registry_path.glob(f"*/skills/*/{DEFAULT_SKILL_CONFIG_FILE}"))


def run_dialogues_check(
    packages_dir: Path,
    ignore: List[str],
    dialogues: List[str],
) -> None:
    """Run dialogues check."""

    try:
        with sys_path_patch(packages_dir.parent):
            load_package_tree(packages_dir=packages_dir)
            for yaml_file in list_all_skill_yaml_files(packages_dir):
                if yaml_file.parent.name in ignore:
                    click.echo(f"Skipping {yaml_file.parent.name}")
                    continue

                click.echo(f"Checking {yaml_file.parent.name}")
                check_dialogues_in_a_skill_package(
                    config_file=yaml_file,
                    dialogues=dialogues,
                )
    except (ValueError, FileNotFoundError, ImportError) as e:
        raise click.ClickException(str(e))


class ParseLogs:
    """Parse agent logs."""

    _dbs: Dict[str, AgentLogsDB]
    _collection: LogCollection
    _db_path: Path

    results: Dict[str, List[LogRow]]

    def __init__(self) -> None:
        """Initialize object."""

    def from_dir(self, logs_dir: Path) -> "ParseLogs":
        """From directory"""

        self._db_path = logs_dir / LOGS_DB
        self._collection = FromDirectory(directory=logs_dir)
        self._dbs = {
            agent: AgentLogsDB(agent=agent, file=self._db_path)
            for agent in self._collection.agents
        }

        return self

    def create_tables(self, reset: bool = False) -> "ParseLogs":
        """Create required tables."""

        for agent, db in self._dbs.items():
            db_exists = db.exists()
            if db_exists and not reset:
                continue

            self._collection.create_agent_db(
                agent=agent,
                db=db,
                reset=reset,
            )

        return self

    def select(  # pylint: disable=too-many-arguments
        self,
        agents: List[str],
        start_time: Optional[Union[str, datetime]],
        end_time: Optional[Union[str, datetime]],
        log_level: Optional[str],
        period: Optional[int],
        round_name: Optional[str],
        behaviour_name: Optional[str],
    ) -> "ParseLogs":
        """Query and return results."""

        if start_time is not None:
            start_time = datetime.strptime(cast(str, start_time), TIME_FORMAT)

        if end_time is not None:
            end_time = datetime.strptime(cast(str, end_time), TIME_FORMAT)

        results = {}
        for agent in agents:
            results[agent] = self._dbs[agent].select(
                start_time=start_time,
                end_time=end_time,
                log_level=log_level,
                period=period,
                round_name=round_name,
                behaviour_name=behaviour_name,
            )

        self.results = results
        return self

    def execution_path(self) -> None:
        """Output FSM path"""
        for agent, logs in self.results.items():
            period = -1
            click.echo(f"Agent {agent}")
            for _, _, message, _, _, _ in logs:
                match = ENTER_ROUND_REGEX.match(message)
                if match is not None:
                    _, _period = cast(Tuple[str, int], match.groups())
                    if _period != period:
                        period = _period
                        click.echo(f"|_ Period {period}")

                match = EXIT_ROUND_REGEX.match(message)
                if match is not None:
                    round_name, exit_event = match.groups()
                    click.echo(f"| |_ {round_name} | {exit_event}")
            click.echo("|_ End\n")

    def table(self) -> None:
        """Print table."""

        for agent, logs in self.results.items():
            click.echo(f"--- {agent} ---")
            for timestamp, log_level, message, _, _, _ in logs:
                click.echo(f"[{timestamp}][{log_level}] {message}")
            click.echo("--- End ---")
