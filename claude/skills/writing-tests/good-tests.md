# Good and bad tests

Reference for `writing-tests`: what separates a test that survives a refactor from one that breaks on it, and how to
design code so its tests replace only what they must.

## Good tests

A good test checks a behaviour a caller cares about, through the public interface, and survives any internal
refactor that keeps that behaviour.

```python
def test_a_customer_can_check_out_a_valid_cart(client):
    cart = create_cart(client, customer_id="c1")
    add_to_cart(client, cart["id"], product_id="p1")
    result = checkout(client, cart["id"], payment_method="pm_test")
    assert result["status"] == "confirmed"
```

```typescript
test('a customer can check out a valid cart', async () => {
  const cart = await createCart(api, { customerId: 'c1' })
  await addToCart(api, cart.id, 'p1')
  expect((await checkout(api, cart.id, 'pm_test')).status).toBe('confirmed')
})
```

- Its name says what the system does, not how.
- It makes one logical assertion.
- It imports nothing from another module's internals.

## Bad tests

A bad test is coupled to the implementation. It breaks when the code is refactored, and it can pass while the
behaviour is broken.

```python
def test_checkout_asks_the_pricing_helper_for_the_total(mocker):
    total = mocker.patch("app.checkout.pricing.total_for")
    checkout(cart, payment_method)
    total.assert_called_once_with(cart)
```

Warning signs:

- It replaces the module's own collaborators.
- It tests a private function.
- It asserts on call counts or call order.
- It verifies through a side door instead of the interface:

```python
# Bad: reads the database behind the interface
def test_create_customer_saves_a_row(db):
    create_customer(name="Ana")
    assert db.execute("SELECT 1 FROM customers WHERE name = 'Ana'").fetchone()

# Good: verifies through the interface
def test_a_created_customer_can_be_retrieved():
    customer = create_customer(name="Ana")
    assert get_customer(customer.id).name == "Ana"
```

## What to replace

Replace only what crosses the module's outbound edge:

- external APIs, such as payment, email and third-party SDKs;
- the clock and randomness;
- a database or filesystem, when a real test instance is too slow to start. Prefer a real test instance.

Never replace the module's own collaborators, another module's public interface, or anything else the project
controls. Needing to replace one is a sign the module boundary is in the wrong place.

## Designing for it

**Pass dependencies in; don't construct them inside.**

```python
# Easy to test: the gateway is a parameter
def process_payment(order, gateway):
    return gateway.charge(order.total)

# Hard to test: the gateway is built inside
def process_payment(order):
    gateway = PaymentGateway(os.environ["PAYMENT_KEY"])
    return gateway.charge(order.total)
```

**Give an external service one method per operation**, not one generic call. Each method can then be replaced on its
own, returns one shape, and the test shows which operations it exercises.

```typescript
// One method per operation
const api = {
  getCustomer: (id: string) => fetch(`/customers/${id}`),
  createOrder: (order: OrderIn) => fetch('/orders', { method: 'POST', body: JSON.stringify(order) }),
}

// One generic call: a replacement needs branching logic
const api = { call: (path: string, init: RequestInit) => fetch(path, init) }
```

**Replace at the lowest stable boundary**, such as the HTTP client, not a helper of the project's own whose
signature will drift.
