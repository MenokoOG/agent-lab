"""The support desk's data and its tool registry. desk_server.py serves this registry over MCP."""
import json
from typing import Dict, List

from agentkit.rag import Index, format_hits
from agentkit.tools import Registry, string_schema

ORDERS: Dict[str, dict] = {
    "1001": {"customer": "Ana", "item": "blue kettle", "status": "shipped", "total": 39},
    "1002": {"customer": "Ben", "item": "desk lamp", "status": "processing", "total": 54},
    "1003": {"customer": "Ana", "item": "wool socks", "status": "delivered", "total": 12},
}

POLICIES: Dict[str, str] = {
    "refunds.txt": "Refunds are issued to the original card within 5 business days. "
                   "A double charge is refunded in full once a human agent approves it.",
    "returns.txt": "Items can be returned within 30 days of delivery. Return shipping is free for damaged items.",
    "shipping.txt": "Standard shipping takes 3 to 5 business days. Express shipping takes 1 to 2 business days.",
    "accounts.txt": "Password resets are sent to the email on file. Reset links expire after 30 minutes.",
}

ESCALATIONS: List[str] = []  # stays inside the desk; nothing here sends outside

registry = Registry("support-desk")
_index = Index(POLICIES, size=160, overlap=30)


@registry.tool("Look up one order by its 4-digit id. Call when the customer gives an order number.",
               string_schema(order_id="The order id, such as 1001"))
def lookup_order(order_id: str) -> str:
    order = ORDERS.get(order_id.strip())
    if order is None:
        raise KeyError(f"no order {order_id}")
    return json.dumps({"order_id": order_id, **order})


@registry.tool("Search the store policies. Call for any question about refunds, returns, shipping or accounts.",
               string_schema(query="The customer's question in a few words"))
def search_policy(query: str) -> str:
    return format_hits(_index.top_k(query, k=2))


@registry.tool("Hand the case to a human agent. Call when you can't answer from the tools.",
               string_schema(reason="One line on why"))
def escalate(reason: str) -> str:
    ESCALATIONS.append(reason)
    return "escalated to a human agent"
