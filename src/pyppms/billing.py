"""Module representing billing information in PPMS."""

from loguru import logger as log

from .common import time_rel_to_abs, fmt_time


VALID_TYPES = ["user", "group", "project"]
"""Accepted types of billing codes."""


class PpmsBillingInformation:
    """Object representing a billing information in PPMS.

    Attributes
    ----------
    billing_code : str
        The billing code / account number.
    billing_type : str
        The type of the billing code, must be one of `user`, `group`, `project`.
    description : str, optional
        An optional description.
    """

    def __init__(
        self,
        billing_code: str,
        billing_type: str,
        description: str = "",
    ):
        if not billing_code:
            raise ValueError("Empty billing codes are not allowed!")
        if not billing_type in VALID_TYPES:
            raise ValueError(f"Billing type has to be one of {VALID_TYPES}!")
        self.billing_code: str = billing_code
        self.billing_type: str = billing_type
        self.description: str = description
        log.trace(str(self))

    def __str__(self) -> str:  # noqa: D105 (undocumented-magic-method)
        msg = (
            f"PpmsBillingInformation(billing_code=[{self.billing_code}], "
            f"billing_type=[{self.billing_type}]"
        )
        if self.description:
            msg += f", description=[{self.description}]"
        msg += ")"

        return msg

    def __eq__(self, other) -> bool:  # noqa: D105 (undocumented-magic-method)
        if not isinstance(other, PpmsBillingInformation):
            return False

        return (
            self.billing_code == other.billing_code
            and self.billing_type == other.billing_type
            and self.description == other.description
        )
