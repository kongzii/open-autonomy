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

"""This module contains the data classes for the reset_pause_abci application."""
from enum import Enum
from typing import Dict, Optional, Set, Tuple, Type

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BasePeriodState,
    BaseTxPayload,
    ABCIAppInternalError,
    TransactionNotValidError,
)
from packages.valory.skills.abstract_round_abci.base import (
    CollectSameUntilThresholdRound,
    DegenerateRound,
)
from packages.valory.skills.reset_pause_abci.payloads import (
    ResetPayload,
)


class Event(Enum):
    """Event enumeration for the reset_pause_abci app."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"


class ResetRound(CollectSameUntilThresholdRound):
    """A round that represents the reset of a period"""

    round_id = "reset"
    allowed_tx_type = ResetPayload.transaction_type
    payload_attribute = "period_count"

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state_data = self.period_state.db.get_all()
            state_data["tx_hashes_history"] = None
            state = self.period_state.update(
                period_count=self.most_voted_payload,
                **state_data,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY
        return None


class ResetAndPauseRound(CollectSameUntilThresholdRound):
    """A round that represents that consensus is reached (the final round)"""

    round_id = "reset_and_pause"
    allowed_tx_type = ResetPayload.transaction_type
    payload_attribute = "period_count"

    def process_payload(self, payload: BaseTxPayload) -> None:  # pragma: nocover
        """Process payload."""

        sender = payload.sender
        if sender not in self.period_state.all_participants:
            raise ABCIAppInternalError(
                f"{sender} not in list of participants: {sorted(self.period_state.all_participants)}"
            )

        if sender in self.collection:
            raise ABCIAppInternalError(
                f"sender {sender} has already sent value for round: {self.round_id}"
            )

        self.collection[sender] = payload

    def check_payload(self, payload: BaseTxPayload) -> None:  # pragma: nocover
        """Check Payload"""

        sender_in_participant_set = payload.sender in self.period_state.all_participants
        if not sender_in_participant_set:
            raise TransactionNotValidError(
                f"{payload.sender} not in list of participants: {sorted(self.period_state.all_participants)}"
            )

        if payload.sender in self.collection:
            raise TransactionNotValidError(
                f"sender {payload.sender} has already sent value for round: {self.round_id}"
            )

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            extra_kwargs = {}
            for key in self.period_state.db.cross_period_persisted_keys:
                extra_kwargs[key] = self.period_state.db.get_strict(key)
            state = self.period_state.update(
                period_count=self.most_voted_payload,
                participants=self.period_state.participants,
                all_participants=self.period_state.all_participants,
                **extra_kwargs,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY
        return None


class FinishedResetAndPauseRound(DegenerateRound):
    """A round that represents reset and pause has finished"""

    round_id = "finished_reset_pause"


class FinishedResetRound(DegenerateRound):
    """A round that represents reset has finished"""

    round_id = "finished_reset"


class ResetPauseABCIApp(AbciApp[Event]):
    """ResetPauseABCIApp

    Initial round: RegistrationRound

    Initial states: {RegistrationRound}

    Transition states:

    0. ResetAndPauseRound
        - done: 2.
        - reset timeout: 0.
        - no majority: 0.
    1. ResetRound
        - done: 2.
        - reset timeout: 0.
        - no majority: 0.
    2. FinishedResetAndPauseRound

    Initial states: {
        ResetRound,
        ResetAndPauseRound,
    }

    Final states: {
        FinishedResetAndPauseRound,
    }

    Timeouts:
        round timeout: 30.0
        reset timeout: 30.0
    """

    initial_round_cls: Type[AbstractRound] = ResetAndPauseRound
    initial_states: Set[AppState] = {
        ResetRound,
        ResetAndPauseRound,
    }
    transition_function: AbciAppTransitionFunction = {
        ResetAndPauseRound: {
            Event.DONE: FinishedResetAndPauseRound,
            Event.RESET_TIMEOUT: ResetAndPauseRound,
            Event.NO_MAJORITY: ResetAndPauseRound,
        },
        ResetRound: {
            Event.DONE: FinishedResetRound,
            Event.RESET_TIMEOUT: ResetRound,
            Event.NO_MAJORITY: ResetRound,
        },
        FinishedResetAndPauseRound: {},
    }
    final_states: Set[AppState] = {
        FinishedResetAndPauseRound,
        FinishedResetRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }
