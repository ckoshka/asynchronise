import asyncio
#from loguru import logger

#print = logger.info
import functools
from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    Set,
    Type,
    Union,
    Tuple,
    Hashable,
)
from uuid import uuid4
from threading import Lock

class Event:
    def __init__(self, data: Any, uuid: str):
        self.data = data
        self.uuid = uuid
        self._lock = Lock()
        self.tag = set()

    # Ideally, we'd like to be able to call methods on and get attributes from the data as if it were the data itself, so we can override getattr and setattr.
    def __getattr__(self, name: str) -> Any:
        if name not in self.__dict__:
            #with self._lock:
            return self.__getattribute__("data").__getattribute__(name)
        return self.__getattribute__(name)

    # And a convenience function for getting the type of the data
    def istype(self, cls: Type) -> bool:
        return isinstance(self.data, cls)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.data}>"


from collections import namedtuple

Conditions = namedtuple("Conditions", ["type", "tag", "predicate"])


class UniqueCollection:
    def __init__(
        self,
        func: Callable,
        keyword_lambdas: Dict[
            str,
            Tuple[
                Union[Type, Tuple[Type], List[Type]],
                Optional[Hashable],
                Optional[Callable[[Event], bool]],
            ],
        ],
        uuid: str,
    ) -> None:
        self.func = func
        self.keyword_lambdas = {k: Conditions(*v) for k, v in keyword_lambdas.items()}
        self.collection: Dict[str, Any] = {k: None for k in keyword_lambdas.keys()}
        self.uuid = uuid
        self.empty_slots = set(self.collection.keys())

    async def check_object(self, obj: Event) -> Optional[Dict[str, Any]]:
        to_remove = set()
        for k in self.empty_slots:
            condition = self.keyword_lambdas[k]
            if (
                (condition.type is None or isinstance(obj.data, condition.type))
                and (condition.tag is None or condition.tag in obj.tag)
                and (condition.predicate is None or condition.predicate(obj))
            ):
                self.collection[k] = obj.data
                to_remove.add(k)
                #print("Added to collection:", k)
            else:
                pass
                #print("Not added to collection:", k, type(obj.data), obj.data)
        self.empty_slots -= to_remove
        if len(self.empty_slots) == 0:
            return self.collection


class FunctionSlot:
    def __init__(
        self,
        func: Callable,
        keyword_lambdas: Dict[
            str,
            Tuple[
                Union[Type, Tuple[Type], List[Type]],
                Optional[Hashable],
                Optional[Callable[[Event], bool]],
            ],
        ],
    ) -> None:
        self.func = func
        self.keyword_lambdas = keyword_lambdas
        self.collection_slots: Dict[str, UniqueCollection] = {}

    async def match_object(self, obj: Event):
        if obj.uuid not in self.collection_slots.keys():
            #print("Creating new collection")
            self.collection_slots[obj.uuid] = UniqueCollection(
                self.func, self.keyword_lambdas, obj.uuid
            )
        collection = self.collection_slots[obj.uuid]
        result = await collection.check_object(obj)
        if result is not None:
            #print("Returning result")
            del self.collection_slots[obj.uuid]
            return (self.func, result)


import inspect


def get_uuid(*args, **kwargs):
    uus = [x.uuid for x in args if isinstance(x, Event)] + [
        v.uuid for k, v in kwargs.items() if isinstance(v, Event)
    ]
    if uus:
        uu = uus[0]
        #print("UUID WAS FOUND IN THE ARGS:", uu)
    else:
        #print("No uuids found")
        uu = uuid4().hex
    return uu

import random
import ast

class Asynchronise:
    def __init__(self, name: str = None) -> None:
        self.functions: Dict[str, FunctionSlot] = {}
        self.senders: Set[str] = set()
        self.name = (
            name
            if name
            else "".join(list(map(lambda x: chr(random.randint(97, 122)), range(10))))
        )

    def send(self, func: Callable) -> Callable:
        self.senders.add(func.__name__)

        async def async_generator_decorator(*args, **kwargs) -> Any:
            uu = get_uuid(*args, **kwargs)
            async for obj in func(*args, **kwargs):
                asyncio.create_task(self.create_event(obj, uu))
                yield obj

        async def sync_generator_decorator(*args, **kwargs) -> Any:
            uu = get_uuid(*args, **kwargs)
            for obj in func(*args, **kwargs):
                asyncio.create_task(self.create_event(obj, uu))
                yield obj

        async def async_function_decorator(*args, **kwargs) -> Any:
            uu = get_uuid(*args, **kwargs)
            obj = await func(*args, **kwargs)
            asyncio.create_task(self.create_event(obj, uu))
            return obj

        async def sync_function_decorator(*args, **kwargs) -> Any:
            uu = get_uuid(*args, **kwargs)
            loop = asyncio.get_running_loop()
            obj = await loop.run_in_executor(
                None, functools.partial(func, *args, **kwargs)
            )
            asyncio.create_task(self.create_event(obj, uu))
            return obj

        if inspect.isasyncgenfunction(func):
            #logger.debug(f"Wrapping {func.__name__} as an async generator")
            async_generator_decorator.__name__ = func.__name__
            async_generator_decorator.__doc__ = func.__doc__
            return async_generator_decorator
        elif inspect.iscoroutinefunction(func):
            #logger.debug(f"Wrapping {func.__name__} as a coroutine")
            async_function_decorator.__name__ = func.__name__
            async_function_decorator.__doc__ = func.__doc__
            return async_function_decorator
        elif inspect.isgeneratorfunction(func):
            #logger.debug(f"Wrapping {func.__name__} as a generator")
            sync_generator_decorator.__name__ = func.__name__
            sync_generator_decorator.__doc__ = func.__doc__
            return sync_generator_decorator
        else:
            #logger.debug(f"Wrapping {func.__name__} as a function")
            sync_function_decorator.__name__ = func.__name__
            sync_function_decorator.__doc__ = func.__doc__
            return sync_function_decorator

    async def create_event(self, obj: Any, uu: str):
        if isinstance(obj, tuple):
            event = Event(obj[0], uu)
            for tag in obj[1:]:
                event.tag.add(tag)
        else:
            event = Event(obj, uu)
        [
            asyncio.create_task(self.check_for_match(func_slot, event, uu))
            for func_slot in self.functions.values()
        ]

    async def check_for_match(self, func_slot: FunctionSlot, event: Event, uu: str):
        res = await func_slot.match_object(event)
        if res:
            func, kwargs = res
            asyncio.create_task(self.schedule_completion(func, kwargs, uu))

    async def schedule_completion(
        self, func: Callable, kwargs: Dict[str, Any], uu: str
    ) -> None:
        # uu = get_uuid(**kwargs)
        if inspect.isasyncgenfunction(func):
            async for obj in func(
                **kwargs
            ):  # this is calling the sender decorator implicitly.
                if func.__name__ in self.senders:
                    asyncio.create_task(self.create_event(obj, uu))
        elif inspect.iscoroutinefunction(func):
            obj = await asyncio.create_task(func(**kwargs))
            if func.__name__ in self.senders:
                asyncio.create_task(self.create_event(obj, uu))
        elif inspect.isgeneratorfunction(func):
            for obj in func(**kwargs):
                if func.__name__ in self.senders:
                    asyncio.create_task(self.create_event(obj, uu))
        else:
            loop = asyncio.get_running_loop()
            obj = await loop.run_in_executor(None, functools.partial(func, **kwargs))
            if func.__name__ in self.senders:
                asyncio.create_task(self.create_event(obj, uu))

    def collect(
        self,
        keyword_lambdas: Dict[
            str,
            Tuple[
                Union[Type, Tuple[Type], List[Type]],
                Optional[Hashable],
                Optional[Callable[[Event], bool]],
            ],
        ],
    ) -> Callable:
        def decorator(func: Callable) -> Callable:
            self.functions[func.__name__] = FunctionSlot(func, keyword_lambdas)
            return func

        return decorator