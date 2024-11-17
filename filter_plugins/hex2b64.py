#!/usr/bin/env python3
"""Custom Ansible filter module definition"""

# pylint: disable=too-few-public-methods

from base64 import b64encode
from typing import Any
from typing import Callable
###############################################################################


def hex2b64(s: str) -> str:
    return b64encode(bytes.fromhex(s)).decode(encoding='ascii')

###############################################################################


class FilterModule:
    """Custom Ansible filter module definition"""

    def filters(self) -> dict[str, Callable[..., Any]]:
        """Ansible filter plugins defined in this module:"""
        return {
            'hex2b64': hex2b64
        }
###############################################################################
