import logging
from yattorrent.actor import ActorSystem

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)


async def main():
    logging.info("Running CLI!")


if __name__ == "__main__":
    ActorSystem.run(main)
