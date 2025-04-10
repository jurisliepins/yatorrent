import logging
from abc import ABC, abstractmethod
import asyncio
from enum import Enum
from typing import Any, Callable, Coroutine


class ActorRef(ABC):
    @abstractmethod
    async def post(self, message: Any) -> None:
        pass

    @abstractmethod
    async def post_with_reply(self, message: Any) -> Any:
        pass


class Letter:
    def __init__(self, message: Any, self_ref: ActorRef, sender_ref: ActorRef) -> None:
        self.message = message
        self.self_ref = self_ref
        self.sender_ref = sender_ref


class MailboxStatus(Enum):
    SUCCESS = 0
    FAILURE = 1


class Mailbox:
    def __init__(self, status: MailboxStatus, letter: Letter) -> None:
        self.status = status
        self.letter = letter


class BlankActor(ActorRef):
    async def post(self, message: Any) -> None:
        pass

    async def post_with_reply(self, message: Any) -> Any:
        pass


BLANK_REF = BlankActor()


class ActorState(Enum):
    CONTINUE = 0
    TERMINATE = 1


type MailboxReceiver = Callable[[Mailbox], Coroutine[Any, Any, ActorState]]


class Awaiter:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)
        self._result = None

    def create_fn(self) -> MailboxReceiver:
        async def fn(mailbox: Mailbox) -> ActorState:
            async with self._lock:
                match mailbox.status:
                    case MailboxStatus.SUCCESS:
                        self._result = mailbox.letter.message
                        self._condition.notify_all()
                    case MailboxStatus.FAILURE:
                        self._result = None
                        self._condition.notify_all()
            return ActorState.TERMINATE

        return fn

    async def result(self) -> Any:
        async with self._condition:
            await self._condition.wait()
        return self._result


class Actor(ActorRef):
    def __init__(self, fn: MailboxReceiver, queue_size: int):
        self._lock = asyncio.Lock()
        self._letters = asyncio.Queue(maxsize=queue_size)
        self._fn = fn

    async def post(self, message: Any, sender_ref=BLANK_REF) -> None:
        async with self._lock:
            await self._letters.put(Letter(message=message, self_ref=self, sender_ref=sender_ref))

    async def post_with_reply(self, message: Any) -> Any:
        awaiter = Awaiter()
        awaiter_ref = ActorSystem.spawn(awaiter.create_fn())
        async with self._lock:
            await self._letters.put(Letter(message=message, self_ref=self, sender_ref=awaiter_ref))
        return await awaiter.result()

    async def run(self) -> None:
        try:
            while True:
                letter = await self._letters.get()
                try:
                    next_state = await self._fn(Mailbox(status=MailboxStatus.SUCCESS, letter=letter))
                    match next_state:
                        case ActorState.TERMINATE:
                            return
                        case _:
                            pass
                except Exception as e:
                    logging.exception("Actor failed to handle a message.", e)
                    try:
                        next_state = await self._fn(Mailbox(status=MailboxStatus.FAILURE, letter=letter))
                        match next_state:
                            case ActorState.TERMINATE:
                                return
                            case _:
                                pass
                    except Exception as e:
                        logging.exception("Actor failed while handling failure. Shutting down.", e)
                        return
        except Exception as e:
            logging.exception("Actor is shutting down due to an error.", e)
            return


class ActorSystem:
    @staticmethod
    def spawn(fn: MailboxReceiver, queue_size=1000000):
        ref = Actor(fn=fn, queue_size=queue_size)
        asyncio.create_task(ref.run())
        return ref

    @staticmethod
    async def shutdown():
        tasks = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def run(fn):
        asyncio.run(fn())
