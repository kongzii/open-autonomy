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

"""Test deployment command."""

import os
import shutil
from pathlib import Path
from typing import Tuple
from unittest import mock

import yaml

from aea_swarm.cli import cli
from aea_swarm.constants import OPEN_AEA_IMAGE_NAME, TENDERMINT_IMAGE_NAME

from tests.conftest import ROOT_DIR
from tests.test_aea_swarm.test_cli.base import BaseCliTest


class TestBuildDeployment(BaseCliTest):
    """Test `swarm deply build deployment` command."""

    cli_options: Tuple[str, ...] = ("deploy", "build", "deployment")
    service_id: str = "valory/oracle_hardhat"

    keys_file: Path

    @classmethod
    def setup(cls) -> None:
        """Setup class."""

        super().setup()

        cls.keys_file = cls.t / "keys.json"

        shutil.copytree(ROOT_DIR / "packages", cls.t / "packages")
        shutil.copy(
            ROOT_DIR / "deployments" / "keys" / "hardhat_keys.json", cls.keys_file
        )

        os.chdir(cls.t)
        cls.cli_runner.invoke(
            cli, ("deploy", "build", "image", "valory/oracle_hardhat", "--dependencies")
        )

    def _build_images(self, version: str = "0.1.0") -> None:
        """Build images."""
        result = self.cli_runner.invoke(
            cli, ("deploy", "build", "image", self.service_id, "--version", version)
        )

        assert result.exit_code == 0, result.output

        result = self.cli_runner.invoke(
            cli,
            (
                "deploy",
                "build",
                "image",
                self.service_id,
                "--version",
                version,
                "--dependencies",
            ),
        )

        assert result.exit_code == 0, result.output

    def test_docker_compose_build(
        self,
    ) -> None:
        """Run tests."""

        with mock.patch("os.chown"):
            result = self.run_cli(
                (
                    self.service_id,
                    str(self.keys_file),
                    "--package-dir",
                    str(self.t / "packages"),
                    "--o",
                    str(self.t),
                    "--force",
                )
            )

        build_dir = self.t / "abci_build"

        assert result.exit_code == 0, f"{result.stdout_bytes}\n{result.stderr_bytes}"
        assert build_dir.exists()

        build_tree = list(map(lambda x: x.name, build_dir.iterdir()))
        assert any(
            [
                child in build_tree
                for child in ["persistent_storage", "nodes", "docker-compose.yaml"]
            ]
        )

        docker_compose_file = build_dir / "docker-compose.yaml"
        with open(docker_compose_file, "r", encoding="utf-8") as fp:
            docker_compose = yaml.safe_load(fp)

        assert any(
            [key in docker_compose for key in ["version", "services", "networks"]]
        )

        assert any(
            [
                service in docker_compose["services"]
                for service in [
                    *map(lambda i: f"abci{i}", range(4)),
                    *map(lambda i: f"node0{i}", range(4)),
                ]
            ]
        )

    def test_kubernetes_build(
        self,
    ) -> None:
        """Run tests."""

        with mock.patch("os.chown"):
            result = self.run_cli(
                (
                    self.service_id,
                    str(self.keys_file),
                    "--package-dir",
                    str(self.t / "packages"),
                    "--o",
                    str(self.t),
                    "--kubernetes",
                    "--force",
                )
            )

        build_dir = self.t / "abci_build"

        assert result.exit_code == 0, f"{result.stdout_bytes}\n{result.stderr_bytes}"
        assert build_dir.exists()

        build_tree = list(map(lambda x: x.name, build_dir.iterdir()))
        assert any(
            [child in build_tree for child in ["persistent_storage", "build.yaml"]]
        )

    def test_versioning_docker_compose(
        self,
    ) -> None:
        """Run tests."""

        version = "1.0.0"
        self._build_images(version)
        with mock.patch("os.chown"):
            result = self.run_cli(
                (
                    self.service_id,
                    str(self.keys_file),
                    "--package-dir",
                    str(self.t / "packages"),
                    "--o",
                    str(self.t),
                    "--force",
                    "--version",
                    version,
                )
            )

        assert result.exit_code == 0, result.output

        build_dir = self.t / "abci_build"
        docker_compose_file = build_dir / "docker-compose.yaml"
        with open(docker_compose_file, "r", encoding="utf-8") as fp:
            docker_compose = yaml.safe_load(fp)

        for i in range(4):
            assert (
                docker_compose["services"][f"node{i}"]["image"]
                == f"{TENDERMINT_IMAGE_NAME}:{version}"
            )
            assert (
                docker_compose["services"][f"abci{i}"]["image"]
                == f"{OPEN_AEA_IMAGE_NAME}:oracle_deployable-{version}"
            )

    def test_versioning_kubernetes(
        self,
    ) -> None:
        """Run tests."""

        version = "1.0.0"
        self._build_images(version)
        with mock.patch("os.chown"):
            result = self.run_cli(
                (
                    self.service_id,
                    str(self.keys_file),
                    "--package-dir",
                    str(self.t / "packages"),
                    "--o",
                    str(self.t),
                    "--force",
                    "--kubernetes",
                    "--version",
                    version,
                )
            )

        assert result.exit_code == 0, result.output

        build_dir = self.t / "abci_build"
        kubernetes_config_file = build_dir / "build.yaml"
        with open(kubernetes_config_file, "r", encoding="utf-8") as fp:
            kubernetes_config = list(yaml.safe_load_all(fp))

        for resource in kubernetes_config:
            try:
                resource["spec"]["template"]["spec"]["containers"][0]["image"]
                resource["spec"]["template"]["spec"]["containers"][1]["image"]
            except (KeyError, IndexError):
                continue

            assert (
                resource["spec"]["template"]["spec"]["containers"][0]["image"]
                == f"{TENDERMINT_IMAGE_NAME}:{version}"
            )

            assert (
                resource["spec"]["template"]["spec"]["containers"][1]["image"]
                == f"{OPEN_AEA_IMAGE_NAME}:oracle_deployable-{version}"
            )

    @classmethod
    def teardown(cls) -> None:
        """Teardown method."""

        os.chdir(cls.cwd)
        super().teardown()