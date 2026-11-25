"""Shared test setup: every test runs with a fake model, so the suite needs no key and spends nothing."""
import unittest

from agentkit import llm


class FakeModelTest(unittest.TestCase):
    """Base class: installs a fake per test and always removes it."""

    def use(self, fake):
        llm.FAKE = fake
        self.addCleanup(setattr, llm, "FAKE", None)
        return fake
