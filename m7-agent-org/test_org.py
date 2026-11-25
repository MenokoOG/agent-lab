import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import llm
import mega
import shop
import team
from compare import REQUESTS, wrong_calls


class OrgTests(unittest.TestCase):
    def tearDown(self):
        llm.FAKE = None

    def test_team_routes_through_a_specialist_to_a_leaf_tool(self):
        # order of model calls: router, orders agent, orders agent, router
        llm.FAKE = llm.scripted(
            llm.fake_tool_use("ask_orders", {"brief": "where is order 1002"}, id="r1"),
            llm.fake_tool_use("get_order", {"order_id": "1002"}, id="o1"),
            llm.fake_text("Order 1002 is processing."),
            llm.fake_text("It is processing."),
        )
        log = []
        answer = team.ask("Where is order 1002?", log)
        self.assertEqual((answer, log), ("It is processing.", ["get_order"]))

    def test_specialists_only_see_their_own_tools(self):
        llm.FAKE = llm.scripted(
            llm.fake_tool_use("ask_catalog", {"brief": "stock?"}, id="r1"),
            llm.fake_text("checked"),
            llm.fake_text("done"),
        )
        team.ask("Is the kettle in stock?", [])
        inner_request = llm.FAKE.bodies[1]
        self.assertEqual({t["name"] for t in inner_request["tools"]}, {"search_products", "get_stock"})
        router_request = llm.FAKE.bodies[0]
        self.assertEqual({t["name"] for t in router_request["tools"]}, {"ask_orders", "ask_catalog"})

    def test_mega_agent_sees_every_tool(self):
        llm.FAKE = llm.scripted(llm.fake_text("ok"))
        mega.ask("hi", [])
        self.assertEqual(len(llm.FAKE.bodies[0]["tools"]), 4)

    def test_logging_and_wrong_call_counting(self):
        log = []
        h = shop.logged(shop.LEAF_HANDLERS, log)
        h["get_stock"](sku="K-100")
        h["list_orders"](customer="Ana")
        self.assertEqual(log, ["get_stock", "list_orders"])
        self.assertEqual(wrong_calls(log, {"get_stock"}), ["list_orders"])

    def test_requests_are_answerable_from_the_data(self):
        self.assertEqual(len(REQUESTS), 8)
        self.assertEqual(json.loads(shop.get_order("1002"))["status"], "processing")
        self.assertEqual(json.loads(shop.get_stock("L-200"))["stock"], 0)


if __name__ == "__main__":
    unittest.main()
