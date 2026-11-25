"""Module 7's shop team, rebuilt with Strands: specialists are agents wrapped as tools ("agents as tools").

    python team.py "Is the blue kettle in stock?"
"""
import sys
from pathlib import Path

from strands import Agent, tool

sys.path.append(str(Path(__file__).resolve().parents[1] / "m7-agent-org"))
import shop  # noqa: E402  (module 7's leaf functions)


@tool
def get_order(order_id: str) -> str:
    """Look up one order by id. Call when the user gives an order number.

    Args:
        order_id: The order id, such as 1001.
    """
    return shop.get_order(order_id)


@tool
def list_orders(customer: str) -> str:
    """List all orders for one customer. Call when the user names a customer.

    Args:
        customer: Customer first name.
    """
    return shop.list_orders(customer)


@tool
def search_products(query: str) -> str:
    """Find products by name. Call to turn a product name into a SKU.

    Args:
        query: Part of a product name.
    """
    return shop.search_products(query)


@tool
def get_stock(sku: str) -> str:
    """Stock level for one SKU. Call after search_products when asked about availability.

    Args:
        sku: A SKU from search_products, such as K-100.
    """
    return shop.get_stock(sku)


def build_team(make_model):
    """make_model() returns a fresh model for each agent. Each specialist only sees its own tools."""
    orders = Agent(model=make_model(), tools=[get_order, list_orders], callback_handler=None,
                   system_prompt="You answer order questions using your tools. Be brief.")
    catalog = Agent(model=make_model(), tools=[search_products, get_stock], callback_handler=None,
                    system_prompt="You answer product and stock questions using your tools. Be brief.")

    @tool
    def ask_orders(brief: str) -> str:
        """Order questions: status, history, what a customer bought. Pass the full request as the brief.

        Args:
            brief: The user's request, in full.
        """
        return str(orders(brief))

    @tool
    def ask_catalog(brief: str) -> str:
        """Product questions: what we sell, stock, availability. Pass the full request as the brief.

        Args:
            brief: The user's request, in full.
        """
        return str(catalog(brief))

    router = Agent(model=make_model(), tools=[ask_orders, ask_catalog], callback_handler=None,
                   system_prompt="You route shop requests to the right specialist, then answer. Be brief.")
    return router, orders, catalog


if __name__ == "__main__":
    from models import make_model
    router, _, _ = build_team(make_model)
    print(router(" ".join(sys.argv[1:]) or "Is the blue kettle in stock?"))
