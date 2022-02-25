Asynchronise lets you turn your functions into fully coordinated, event-driven async generators that yield their results mid-step, allowing other functions (both synchronous and asynchronous, generators or non-generators) to use them immediately.

It's ideal if you need a small, tidy, async and sync-compatible framework for managing events with runtime type-checking. Or if you really love decorators.

## Installing

```bash
pip install git+https://github.com/ckoshka/asynchronise
```

## Example

```python
from asynchronise import Asynchronise

asy = Asynchronise()

@asy.send
async def do_expensive_multistep_stuff():
    flour: Ingredient[Flour] = await go_to_the_store()
    yield flour

    egg: Egg = await get_eggs(variety="scrambled")
    yield eggs, "scrambled"

    egg: Egg = await get_eggs(variety="raw")
    yield eggs, "raw"

    milk: Ingredient[Milk] = await get_milk()
    yield milk, "liquid"

@asy.collect({
    "egg": (Egg, "scrambled", lambda egg: egg.weight > 100)
})
def eat_egg(egg):
    # This won't block the event loop 
    time.sleep(10) 
    print("Yummy!")
    
@asy.send
@asy.collect({
    "orders": (int, "customer_order", None),
    "flour": (Flour, None, lambda flour: flour.type == "rye"),
    "liquid": (None, "liquid", None)
})
async def make_dough(orders, flour, liquid):
    # I don't actually understand how making bread works, sorry to any bakers out there.
    for order_num in range(orders):
        await liquid.stir()
        dough = await flour.mix(liquid)
        yield dough, order_num
    
```