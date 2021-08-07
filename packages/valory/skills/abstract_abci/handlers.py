# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021 Valory AG
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

"""This module contains the handler for the 'abci' skill."""
from typing import List, cast

from aea.protocols.base import Message
from aea.skills.base import Handler

from packages.valory.protocols.abci import AbciMessage
from packages.valory.protocols.abci.custom_types import (
    Events,
    ProofOps,
    ValidatorUpdates,
)
from packages.valory.protocols.abci.dialogues import AbciDialogue, AbciDialogues


class ABCIHandler(Handler):
    """ABCI handler."""

    SUPPORTED_PROTOCOL = AbciMessage.protocol_id

    def setup(self) -> None:
        """Set up the handler."""
        self.context.logger.info("ABCI Handler: setup method called.")

    def handle(self, message: Message) -> None:
        """
        Handle the message.

        :param message: the message.
        """
        abci_message = cast(AbciMessage, message)

        # recover dialogue
        abci_dialogues = cast(AbciDialogues, self.context.abci_dialogues)
        abci_dialogue = cast(AbciDialogue, abci_dialogues.update(message))

        if abci_dialogue is None:
            self.send_exception(abci_message, "Invalid dialogue.")
            return

        performative = message.performative.value
        # if the message is of type "response", send error.
        if "response_" in performative:
            self.send_exception(
                abci_message,
                f"can only handle ABCI requests, received '{message.performative.value}'",
            )
            return

        # handle message
        request_type = performative.replace("request_", "")
        self.context.logger.info(f"Received ABCI request of type {request_type}")
        handler = getattr(self, request_type, None)
        if handler is None:
            self.context.logger.warning(
                f"cannot handle request '{request_type}', ignoring..."
            )
            return

        self.context.logger.info(
            "ABCI Handler: message={}, sender={}".format(message, message.sender)
        )
        response = handler(message, abci_dialogue)
        self.context.outbox.put_message(message=response)

    def teardown(self) -> None:
        """Teardown the handler."""
        self.context.logger.info("ABCI Handler: teardown method called.")

    def send_exception(self, message: AbciMessage, error_message: str) -> None:
        """Send a response exception."""
        self.context.logger.info(
            f"Sending a response exception message with error message: {error_message}"
        )
        abci_dialogues = cast(AbciDialogues, self.context.abci_dialogues)
        reply, _ = abci_dialogues.create(
            counterparty=message.sender,
            performative=AbciMessage.Performative.RESPONSE_EXCEPTION,
            error=error_message,
        )
        self.context.outbox.put_message(message=reply)

    def info(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_INFO performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        info_data = ""
        version = ""
        app_version = 0
        last_block_height = 0
        last_block_app_hash = b""
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_INFO,
            target_message=message,
            info_data=info_data,
            version=version,
            app_version=app_version,
            last_block_height=last_block_height,
            last_block_app_hash=last_block_app_hash,
        )
        return cast(AbciMessage, reply)

    def flush(  # pylint: disable=no-self-use
        self,
        message: AbciMessage,
        dialogue: AbciDialogue,  # pylint: disable=unused-argument
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_FLUSH performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_FLUSH,
            target_message=message,
        )
        return cast(AbciMessage, reply)

    def init_chain(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_INIT_CHAIN performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        validators: List = []
        app_hash = b""
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_INIT_CHAIN,
            target_message=message,
            validators=ValidatorUpdates(validators),
            app_hash=app_hash,
        )
        return cast(AbciMessage, reply)

    def query(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_QUERY performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_QUERY,
            target_message=message,
            code=0,
            log="",
            info="",
            index=0,
            key=b"",
            value=b"",
            proof_ops=ProofOps([]),
            height=0,
            codespace="",
        )
        return cast(AbciMessage, reply)

    def check_tx(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_CHECK_TX performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_CHECK_TX,
            target_message=message,
            code=0,  # OK
            data=b"",
            log="",
            info="",
            gas_wanted=0,
            gas_used=0,
            events=Events([]),
            codespace="",
        )
        return cast(AbciMessage, reply)

    def deliver_tx(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_DELIVER_TX performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_DELIVER_TX,
            target_message=message,
            code=0,  # OK
            data=b"",
            log="",
            info="",
            gas_wanted=0,
            gas_used=0,
            events=Events([]),
            codespace="",
        )
        return cast(AbciMessage, reply)

    def begin_block(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_BEGIN_BLOCK performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_BEGIN_BLOCK,
            target_message=message,
            events=Events([]),
        )
        return cast(AbciMessage, reply)

    def end_block(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_END_BLOCK performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_END_BLOCK,
            target_message=message,
            validator_updates=ValidatorUpdates([]),
            events=Events([]),
        )
        return cast(AbciMessage, reply)

    def commit(  # pylint: disable=no-self-use
        self, message: AbciMessage, dialogue: AbciDialogue
    ) -> AbciMessage:
        """
        Handle a message of REQUEST_COMMIT performative.

        :param message: the ABCI request.
        :param dialogue: the ABCI dialogue.
        :return: the response.
        """
        reply = dialogue.reply(
            performative=AbciMessage.Performative.RESPONSE_COMMIT,
            target_message=message,
            data=b"",
            retain_height=0,
        )
        return cast(AbciMessage, reply)