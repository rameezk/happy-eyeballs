import anyio
import socket


async def open_tcp_socket(hostname, port, *, max_wait_time=0.25):
    targets = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    failed_attempts = [anyio.create_event() for _ in targets]
    winning_client = None

    async def attempt(target_idx: int, task_group: anyio.TaskGroup):
        print(f"Trying target index = {target_idx}")

        if target_idx > 0:
            async with anyio.move_on_after(max_wait_time):
                await failed_attempts[target_idx - 1].wait()

        if target_idx + 1 < len(targets):
            await task_group.spawn(attempt, target_idx + 1, task_group)

        try:
            *socket_config, _, target = targets[target_idx]
            client = await anyio.connect_tcp(target[0], target[1])
        except OSError:
            await failed_attempts[target_idx].set()
        else:
            nonlocal winning_client
            winning_client = client
            await task_group.cancel_scope.cancel()

    async with anyio.create_task_group() as tg:
        await tg.spawn(attempt, 0, tg)

    if winning_client is None:
        raise OSError("oh-no")
    else:
        return winning_client


async def main():
    client = await open_tcp_socket("debian.org", "https")
    print(client)


if __name__ == "__main__":
    anyio.run(main)
