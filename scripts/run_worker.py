import asyncio

from apps.worker.main import run_worker

if __name__ == "__main__":
    asyncio.run(run_worker())
