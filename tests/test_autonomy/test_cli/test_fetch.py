# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2022 Valory AG
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

"""Test fetch command."""

import json
import os
import shutil
from pathlib import Path
from typing import Any
from unittest import mock

from aea.helpers.base import cd
from aea.helpers.io import open_file

from autonomy.cli.helpers.registry import IPFSTool

from tests.conftest import ROOT_DIR
from tests.test_autonomy.test_cli.base import BaseCliTest, cli


IPFS_REGISTRY = "/dns/registry.autonolas.tech/tcp/443/https"


class TestFetchCommand(BaseCliTest):
    """Test fetch command."""

    packages_dir: Path

    def setup(self) -> None:
        """Setup class."""

        super().setup()

        self.packages_dir = self.t / "packages"
        self.cli_options = (
            "--registry-path",
            str(self.packages_dir),
            "fetch",
            "--service",
        )

        shutil.copytree(ROOT_DIR / "packages", self.packages_dir)
        os.chdir(self.t)

    def get_service_hash(
        self,
    ) -> str:
        """Load hashes from CSV file."""

        hashes_file = self.packages_dir / "packages.json"
        with open(str(hashes_file), "r") as file:
            hashes = json.load(file)
        return hashes["service/valory/counter/0.1.0"]

    def test_fetch_service_local(
        self,
    ) -> None:
        """Test fetch service."""

        service = self.t / "counter"
        result = self.run_cli(("--local", "valory/counter"))

        assert result.exit_code == 0, result.output
        assert service.exists()

        result = self.run_cli(("--local", "valory/counter"))
        assert result.exit_code == 1, result.output
        assert (
            'Item "counter" already exists in target folder' in result.output
        ), result.output

        shutil.rmtree(service)

    def test_publish_and_fetch_service_ipfs(self, capsys: Any) -> None:
        """Test fetch service."""
        expected_hash = "bafybeidbk4dp3ohvhr24barbi47kmibhn34g5wgo5jcyxwmzmiqdbp3sy4"

        service_dir = self.t / "dummy_service"
        service_file = service_dir / "service.yaml"
        service_dir.mkdir()

        with open_file(
            ROOT_DIR
            / "tests"
            / "data"
            / "dummy_service_config_files"
            / "service_2.yaml"
        ) as fp:
            content = fp.read()

        with open_file(service_file, mode="w") as fp:
            fp.write(content)

        with mock.patch(
            "autonomy.cli.helpers.registry.get_default_remote_registry",
            new=lambda: "ipfs",
        ), mock.patch(
            "autonomy.cli.helpers.registry.get_ipfs_node_multiaddr",
            new=lambda: IPFS_REGISTRY,
        ), cd(
            service_dir
        ):
            result = self.cli_runner.invoke(cli, ["publish", "--remote"])
            output = capsys.readouterr()

            assert result.exit_code == 0, output
            assert expected_hash in output.out, output.err

        with mock.patch(
            "autonomy.cli.helpers.registry.get_default_remote_registry",
            new=lambda: "http",
        ), cd(service_dir):
            result = self.run_cli(("--remote", expected_hash))
            assert result.exit_code == 1, result.output
            assert "HTTP registry not supported." in result.output, result.output

        with mock.patch(
            "autonomy.cli.helpers.registry.get_default_remote_registry",
            new=lambda: "ipfs",
        ), mock.patch(
            "autonomy.cli.helpers.registry.get_ipfs_node_multiaddr",
            new=lambda: IPFS_REGISTRY,
        ), cd(
            service_dir
        ):
            result = self.run_cli(("--remote", expected_hash))
            assert result.exit_code == 0, result.output
            assert service_dir.exists()

        shutil.rmtree(service_dir)

    def test_not_a_service_package(
        self,
    ) -> None:
        """Test fetch service."""
        with mock.patch(
            "autonomy.cli.helpers.registry.get_default_remote_registry",
            new=lambda: "ipfs",
        ), mock.patch(
            "autonomy.cli.helpers.registry.get_ipfs_node_multiaddr",
            new=lambda: IPFS_REGISTRY,
        ), mock.patch.object(
            IPFSTool, "download", return_value=self.t
        ):
            result = self.run_cli(
                (
                    "--remote",
                    "bafybeicqvwvogloyw2ujhedbwv4opn2ngus6dh7ocxg7umhhawcnzpibrq",
                )
            )
            assert result.exit_code == 1, result.output
            assert (
                "Downloaded packages is not a service package, "
                "if you intend to download an agent please use "
                "`--agent` flag or check the hash"
            ) in result.output
