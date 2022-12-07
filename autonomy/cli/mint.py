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

"""Mint command group definitions."""

from pathlib import Path
from typing import Optional, Tuple, cast

import click
from aea.cli.utils.context import Context
from aea.cli.utils.decorators import pass_ctx
from aea.configurations.data_types import PackageType

from autonomy.chain.config import ChainType
from autonomy.cli.helpers.chain import mint_component
from autonomy.cli.utils.click_utils import PathArgument, chain_selection_flag_


package_path_decorator = click.argument(
    "package_path",
    type=PathArgument(exists=True, file_okay=False, dir_okay=True),
)
key_path_decorator = click.argument(
    "keys",
    type=PathArgument(exists=True, file_okay=True, dir_okay=False),
)
password_decorator = click.option(
    "--password",
    type=str,
    help="Password for key pair",
)
dependencies_decorator = click.option(
    "-d",
    "--dependencies",
    type=str,
    multiple=True,
    help="Password for key pair",
)
nft_decorator = click.option(
    "--nft",
    type=str,
    help="IPFS hash for the NFT image",
)


@click.group("mint")
@pass_ctx
@chain_selection_flag_()
def mint(ctx: Context, chain_type: str) -> None:
    """Mint component on-chain."""

    ctx.config["chain_type"] = ChainType(chain_type)


@mint.command()
@package_path_decorator
@key_path_decorator
@password_decorator
@dependencies_decorator
@nft_decorator
@pass_ctx
def protocol(
    ctx: Context,
    package_path: Path,
    keys: Path,
    password: Optional[str],
    dependencies: Tuple[str],
    nft: Optional[str],
) -> None:
    """Mint a protocol component."""

    mint_component(
        package_path=package_path,
        package_type=PackageType.PROTOCOL,
        keys=keys,
        chain_type=cast(ChainType, ctx.config.get("chain_type")),
        dependencies=list(map(int, dependencies)),
        password=password,
        nft_image_hash=nft,
    )
