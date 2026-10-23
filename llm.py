"""Raw Messages API call shared by modules 2 to 10. Standard library only, no SDK.

Tests set llm.FAKE to a function (request body -> response dict), so nothing touches the network.
"""
import copy
import json
import os
import urlib.request
import urlib.error

