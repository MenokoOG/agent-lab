"""The leaf tools for a small online shop. Both the mega-agent and the team use these."""
import json

ORDERS = {
    "1001": {"customer": "Ana", "item": "blue kettle", "status": "shipped"},
    "1002": {"customer": "Ben", "item": "desk lamp", "status": "processing"},
    "1003": {"customer": "Ana", "item": "wool socks", "status": "delivered"},
}
PRODUCTS = {
    "K-100": {"name": "blue kettle", "stock": 12},
    "L-200": {"name": "desk lamp", "stock": 0},
    "S-300": {"name": "wool socks", "stock": 140},
}


def get_order(order_id):
    return json.dumps(ORDERS.get(order_id, "not found"))


def list_orders(customer):
    return json.dumps({k: v for k, v in ORDERS.items() if v["customer"].lower() == customer.lower()})


def search_products(query):
    return json.dumps({k: v["name"] for k, v in PRODUCTS.items() if query.lower() in v["name"]})


def get_stock(sku):
    return json.dumps(PRODUCTS.get(sku, "not found"))


def _schema(**props):
    return {"type": "object", "properties": {k: {"type": "string", "description": v} for k, v in props.items()},
            "required": list(props)}


ORDER_TOOLS = [
    {"name": "get_order", "description": "Look up one order by id. Call when the user gives an order number.",
     "input_schema": _schema(order_id="The order id, such as 1001")},
    {"name": "list_orders", "description": "List all orders for one customer. Call when the user names a customer.",
     "input_schema": _schema(customer="Customer first name")},
]
CATALOG_TOOLS = [
    {"name": "search_products", "description": "Find products by name. Call to turn a product name into a SKU.",
     "input_schema": _schema(query="Part of a product name")},
    {"name": "get_stock", "description": "Stock level for one SKU. Call after search_products when asked about availability.",
     "input_schema": _schema(sku="A SKU from search_products, such as K-100")},
]
LEAF_TOOLS = ORDER_TOOLS + CATALOG_TOOLS
LEAF_HANDLERS = {"get_order": get_order, "list_orders": list_orders,
                 "search_products": search_products, "get_stock": get_stock}


def logged(handlers: dict, log: list) -> dict:
    """Wrap handlers so every leaf call is recorded. This is how compare.py counts wrong-tool calls."""
    def wrap(name, fn):
        def inner(**kw):
            log.append(name)
            return fn(**kw)
        return inner
    return {n: wrap(n, fn) for n, fn in handlers.items()}
