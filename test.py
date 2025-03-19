#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys

# Configuration defaults
CONFIG = {
    "image_name": "elephant-server:0.6.2",
    "workspace": os.path.join(os.getcwd(), "workspace"),
    "gpu": "all",
    "batch_id": "0",
    "http_port": "8080",
    "redis_port": "6379",
    "rabbit_port": "5672",
    "rabbit_mgmt_port": "15672",
    "notebook_port": "8888",
    "rabbit_user": "user",
    "rabbit_password": "user",
    "docker": "docker"
}

def run(cmd):
    print(f">> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def rebuild():
    image_id = subprocess.getoutput(f"{CONFIG['docker']} images -q {CONFIG['image_name']}")
    run(f"{CONFIG['docker']} build --no-cache -t {CONFIG['image_name']} .")
    if image_id:
        run(f"{CONFIG['docker']} rmi {image_id}")

def build():
    run(f"{CONFIG['docker']} build -t {CONFIG['image_name']} .")
    run(f"{CONFIG['docker']} image prune -f")        

def run(cmd):
    print(f">> {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def warmup():
    if CONFIG['gpu']:
        run(f"{CONFIG['docker']} run -it --rm --gpus \"device={CONFIG['gpu']}\" {CONFIG['image_name']} echo 'warming up GPU...'")
    else:
        print("CPU mode...")


def stop():
    container_id = subprocess.getoutput(f"{CONFIG['docker']} ps -aq --filter ancestor={CONFIG['image_name']}")
    if container_id:
        run(f"{CONFIG['docker']} stop {container_id}")



def launch():
    gpu_arg = f"--gpus \"device={CONFIG['gpu']}\"" if CONFIG['gpu'] else ""
    cmd = f"""{CONFIG['docker']} run -it --rm {gpu_arg} --shm-size=8g -v {CONFIG['workspace']}:/workspace \
    -p {CONFIG['http_port']}:{CONFIG['http_port']} \
    -p {CONFIG['rabbit_port']}:{CONFIG['rabbit_port']} \
    -p {CONFIG['rabbit_mgmt_port']}:{CONFIG['rabbit_mgmt_port']} \
    -e RABBITMQ_NODENAME=rabbit@localhost \
    -e RABBITMQ_USER={CONFIG['rabbit_user']} \
    -e RABBITMQ_PASSWORD={CONFIG['rabbit_password']} \
    {CONFIG['image_name']}"""
    run(cmd)

def bash():
    gpu_arg = f"--gpus \"device={CONFIG['gpu']}\"" if CONFIG['gpu'] else ""
    cmd = f"""{CONFIG['docker']} run -it --rm {gpu_arg} --shm-size=8g -v {CONFIG['workspace']}:/workspace \
    -e AS_LOCAL_USER=1 {CONFIG['image_name']} /bin/bash"""
    run(cmd)

def notebook():
    gpu_arg = f"--gpus \"device={CONFIG['gpu']}\"" if CONFIG['gpu'] else ""
    cmd = f"""{CONFIG['docker']} run -it --rm {gpu_arg} --shm-size=8g -v {CONFIG['workspace']}:/workspace \
    --network host -p {CONFIG['notebook_port']}:{CONFIG['notebook_port']} \
    {CONFIG['image_name']} jupyter notebook --no-browser --port={CONFIG['notebook_port']} --notebook-dir=/workspace"""
    run(cmd)

def test():
    run(f"{CONFIG['docker']} build -t {CONFIG['image_name']}-test -f Dockerfile-test .")
    run(f"{CONFIG['docker']} image prune -f")
    run(f"{CONFIG['docker']} run --rm {CONFIG['image_name']}-test")

# CLI dispatcher
TASKS = {
    "build": build,
    "rebuild": rebuild,
    "stop": stop,
    "warmup": warmup,
    "launch": launch,
    "bash": bash,
    "notebook": notebook,
    "test": test
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unified Task Runner")
    parser.add_argument("task", help="Task to run", choices=TASKS.keys())
    args = parser.parse_args()

    try:
        TASKS[args.task]()
    except subprocess.CalledProcessError:
        sys.exit(1)
