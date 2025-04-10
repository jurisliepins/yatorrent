import unittest

from yattorrent.actor import ActorSystem, Mailbox, ActorState, MailboxStatus


async def blank_fn(mailbox: Mailbox) -> ActorState:
    match mailbox.status:
        case MailboxStatus.SUCCESS:
            return ActorState.CONTINUE
        case MailboxStatus.FAILURE:
            return ActorState.TERMINATE
        case _:
            raise Exception("Unknown mailbox status!")


class TestActors(unittest.IsolatedAsyncioTestCase):
    async def test_spawn_actor(self):
        ref = ActorSystem.spawn(blank_fn)


if __name__ == "__main__":
    unittest.main()
