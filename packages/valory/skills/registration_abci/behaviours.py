# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2022 Valory AG
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

"""This module contains the behaviours for the 'abci' skill."""
import json
from typing import Dict, Generator, List, Optional, Set, Type, Union, cast

from packages.valory.contracts.service_registry.contract import ServiceRegistryContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.protocols.tendermint import TendermintMessage
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.abstract_round_abci.models import Requests
from packages.valory.skills.registration_abci.dialogues import (
    TendermintDialogue,
    TendermintDialogues,
)
from packages.valory.skills.registration_abci.payloads import RegistrationPayload
from packages.valory.skills.registration_abci.rounds import (
    AgentRegistrationAbciApp,
    RegistrationRound,
    RegistrationStartupRound,
)


TendermintParams = Dict[
    str,
    Union[
        str,  # proxy_app, p2p_laddr, rpc_laddr
        List[str],  # p2p_seeds
        bool,  # consensus_create_empty_blocks
        Optional[str],  # home
    ],
]


class RegistrationBaseBehaviour(BaseState):
    """Register to the next periods."""

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Build a registration transaction.
        - Send the transaction and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour state (set done event).
        """

        with self.context.benchmark_tool.measure(self.state_id).local():
            initialisation = (
                json.dumps(self.period_state.db.initial_data, sort_keys=True)
                if self.period_state.db.initial_data != {}
                else None
            )
            payload = RegistrationPayload(
                self.context.agent_address, initialisation=initialisation
            )

        with self.context.benchmark_tool.measure(self.state_id).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class RegistrationStartupBehaviour(RegistrationBaseBehaviour):
    """Register to the next periods."""

    state_id = "registration_startup"
    matching_round = RegistrationStartupRound
    collected: Dict[str, str] = dict()
    local_tendermint_params: Optional[TendermintParams] = None
    ENCODING: str = "utf-8"

    @property
    def registered_addresses(self) -> Dict[str, str]:
        """Agent addresses registered on-chain for the service"""
        return self.period_state.db.initial_data.get("registered_addresses", {})

    @property
    def tendermint_parameter_url(self) -> str:
        """Tendermint URL for obtaining and updating parameters"""
        return f"{self.params.tendermint_com_url}/params"

    def is_correct_contract(self) -> Generator[None, None, bool]:
        """Contract deployment verification."""

        performative = ContractApiMessage.Performative.GET_STATE
        contract_api_response = yield from self.get_contract_api_response(
            performative=performative,  # type: ignore
            contract_address=self.params.service_registry_address,
            contract_id=str(ServiceRegistryContract.contract_id),
            contract_callable="verify_contract",
        )
        if contract_api_response.performative != performative:
            self.context.logger.warning("`verify_contract` call unsuccessful!")
            return False
        return cast(bool, contract_api_response.state.body["verified"])

    def get_service_info(self) -> Generator[None, None, dict]:
        """Get service info available on-chain"""

        performative = ContractApiMessage.Performative.GET_STATE
        contract_api_response = yield from self.get_contract_api_response(
            performative=performative,  # type: ignore
            contract_address=self.params.service_registry_address,
            contract_id=str(ServiceRegistryContract.contract_id),
            contract_callable="get_service_info",
            service_id=self.params.on_chain_service_id,
        )
        if contract_api_response.performative != performative:
            self.context.logger.warning("get_service_info unsuccessful!")
            return {}
        return cast(dict, contract_api_response.state.body["verified"])

    def get_addresses(self) -> Generator[None, None, bool]:
        """Get addresses of agents registered for the service"""

        if self.params.service_registry_address is None:
            raise RuntimeError("Service registry contract address not provided")

        is_deployed = yield from self.is_correct_contract()
        if not is_deployed:
            self.context.logger.info("Service registry contract not deployed")
            return False

        # checks if service exists
        service_info = yield from self.get_service_info()
        if not service_info:
            self.context.logger.info("Service info could not be retrieved")
            return False

        # put service info in the shared state for p2p message handler
        registered_addresses = set(service_info["agent_instances"])
        if not registered_addresses:
            log_msg = f"No agent instances registered:\n{service_info}"
            self.context.logger.info(log_msg)
            return False

        my_address = self.context.agent_address
        if my_address not in registered_addresses:
            log_msg = f"You ({my_address}) are not registered:\n{service_info}"
            self.context.logger.info(log_msg)
            return False

        # setup storage for collected tendermint configuration info
        info: Dict[str, str] = dict.fromkeys(registered_addresses)
        info[self.context.agent_address] = self.context.params.tendermint_url

        self.period_state.db.initial_data.update(dict(registered_addresses=info))
        log_msg = "Registered addresses retrieved from service registry contract"
        self.context.logger.info(log_msg)
        return True

    def make_tendermint_request(self, address: str) -> None:
        """Make Tendermint callback request"""

        dialogues = cast(TendermintDialogues, self.context.tendermint_dialogues)
        performative = TendermintMessage.Performative.REQUEST
        message, dialogue = dialogues.create(
            counterparty=address, performative=performative
        )
        message = cast(TendermintMessage, message)
        dialogue = cast(TendermintDialogue, dialogue)
        self.context.outbox.put_message(message=message)
        nonce = self._get_request_nonce_from_dialogue(dialogue)
        requests = cast(Requests, self.context.requests)
        requests.request_id_to_callback[nonce] = self.get_callback_request()

    def get_tendermint_configuration(self) -> Generator[None, None, bool]:
        """Make HTTP GET request to obtain agent's local Tendermint node parameters"""

        url = self.tendermint_parameter_url
        message, dialogue = self._build_http_request_message(method="GET", url=url)
        result = yield from self._do_request(message, dialogue)
        try:
            response = json.loads(result.body.decode())
            self.local_tendermint_params = response
            self.context.logger.info("Local Tendermint configuration obtained")
            return True
        except json.JSONDecodeError:
            self.context.logger.info("Error communicating with Tendermint server")
            return False

    def update_tendermint_configuration(self) -> Generator[None, None, bool]:
        """Make HTTP POST request to update agent's local Tendermint node"""

        url = self.tendermint_parameter_url
        params = cast(TendermintParams, self.local_tendermint_params)
        params["p2p_seeds"] = list(self.registered_addresses.values())
        content = str(params).encode(self.ENCODING)
        message, dialogue = self._build_http_request_message(
            method="POST", url=url, content=content
        )
        result = yield from self._do_request(message, dialogue)
        try:
            response = json.loads(result.body.decode())
            self.context.logger.info("Local TendermintNode started")
            return response["status"] == 200
        except json.JSONDecodeError:
            self.context.logger.info("Error communicating with tendermint server")
            return False

    def start_tendermint(self) -> Generator[None, None, bool]:
        """Start up local Tendermint node"""

        url = self.params.tendermint_com_url + "/start"
        message, dialogue = self._build_http_request_message("GET", url)
        result = yield from self._do_request(message, dialogue)
        try:
            response = json.loads(result.body.decode())
            if response.get("status") == 200:
                self.context.logger.info(response.get("message"))
                return True
            error_message = f"Error starting Tendermint: {response}"
            self.context.logger.error(error_message)
            yield from self.sleep(self.params.sleep_time)
            return False
        except json.JSONDecodeError:
            error_message = "Error communicating with Tendermint server"
            self.context.logger.error(error_message)
            yield from self.sleep(self.params.sleep_time)
            return False

    def async_act(self) -> Generator:
        """Act asynchronously"""

        # collect personal tendermint configuration
        if not self.local_tendermint_params:
            successful = yield from self.get_tendermint_configuration()
            if not successful:
                yield from self.sleep(self.params.sleep_time)
                return

        # make service registry calls
        if not self.registered_addresses:
            successful = yield from self.get_addresses()
            if not successful:
                yield from self.sleep(self.params.sleep_time)
                return

        # request tendermint config information from all agents
        not_yet_collected = set(self.registered_addresses).difference(self.collected)
        any(map(self.make_tendermint_request, not_yet_collected))  # consume

        # if not complete, continue collecting next async_act call
        if set(self.registered_addresses).difference(self.collected):
            yield from self.sleep(self.params.sleep_time)
            return

        # all information collected, update configuration
        successful = yield from self.update_tendermint_configuration()
        if not successful:
            yield from self.sleep(self.params.sleep_time)
            return

        # restart Tendermint with updated configuration
        successful = yield from self.start_tendermint()
        if not successful:
            yield from self.sleep(self.params.sleep_time)
            return

        yield from super().async_act()


class RegistrationBehaviour(RegistrationBaseBehaviour):
    """Register to the next periods."""

    state_id = "registration"
    matching_round = RegistrationRound


class AgentRegistrationRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the registration."""

    initial_state_cls = RegistrationStartupBehaviour
    abci_app_cls = AgentRegistrationAbciApp  # type: ignore
    behaviour_states: Set[Type[BaseState]] = {  # type: ignore
        RegistrationBehaviour,  # type: ignore
        RegistrationStartupBehaviour,  # type: ignore
    }
