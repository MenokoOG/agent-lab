# Whiteboard: online shop operations desk

This is an example. Redo it for a domain you know, then compare.

## Step 1: everything the agent should do (18 capabilities)

1. Look up an order by id
2. List a customer's orders
3. Check order status and tracking
4. Cancel an order before it ships
5. Start a refund
6. Change a shipping address
7. Search products by name
8. Check stock for a SKU
9. Recommend similar products
10. Explain a product's specs
11. Answer shipping-time questions
12. Explain the return policy
13. Look up a customer's account email
14. Reset a customer's password
15. Flag a suspicious order
16. Write a customer apology message
17. Summarize a day's tickets for the manager
18. Draft a restock request for a supplier

## Step 2 and 3: group by data source, job title and step in the process

| Group | Capabilities | Natural division |
| --- | --- | --- |
| Orders | 1, 2, 3, 4, 6, 15 | Order system, "fulfillment" role |
| Catalog | 7, 8, 9, 10, 18 | Product database, "merchandising" role |
| Money | 5, 12 | Payments, needs approval (module 5 checkpoint) |
| Account | 13, 14 | Identity data, highest security risk (module 10) |
| Writing | 11, 16, 17 | No data source, pure generation |

## Step 4: agents, ranked

1. **Orders agent** (burning problem: most tickets are "where is my order"). Build first.
2. **Catalog agent** (second most common question). Build second.
3. **Router** in front of both, once there are two.
4. Money and Account stay out until module 5 and module 10 are done. They need approval and guardrails first.
5. Writing becomes a step inside workflows, not a separate agent.

## Evolve log (fill in as you go)

- Built Orders and Catalog behind a router. Note what changed in routing when you add the third specialist.
