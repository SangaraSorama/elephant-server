#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys

# Configuration defaults
CONFIG = {
    "elephant_gpu": "all", # 0
    "elephant_workspace": os.path.join(os.getcwd(), "workspace"), # 1
    "elephant_image_name": "elephant-server:0.6.2", # 2
    "elephant_nvidia_gid": "$$(ls -n /dev/nvidia0 2>/dev/null | awk '{print $$4}')",  # 3 !!!
    "elephant_docker": "docker", # 4
    "elephant_rabbitmq_nodename": "rabbit@localhost", # 5 !!!
    "elephant_rabbitmq_node_port": "5672", # 6
    "elephant_rabbitmq_management_port": "15672", # 7
    "elephant_rabbitmq_user": "user", # 8
    "elephant_rabbitmq_password": "user", # 9
    "elephant_rabbitmq_pid_file": "/var/lib/rabbitmq/mnesia/rabbitmq.pid", # 10 !!!
    "elephant_redis_port": "6379", # 11
    "elephant_http_port": "8080", # 12
    "elephant_notebook_port": "8888", # 13
    "elephant_batch_id": "0" # 14
}


"""_summary_
    the function to mimic the bash-like run
    
    Args : 
    cmd : the bash function
    shout = False : if untrue, display the function in the cmd
"""
def run(cmd, shout = False):
    if shout : 
        print(f">> {cmd}")
    subprocess.run(cmd, shell=True, check=True)


"""_summary_
    rebuild the docker image without using cache and remove the old image
"""
def rebuild():
    image_id = subprocess.getoutput(f"{CONFIG['elephant_docker']} images -q {CONFIG['elephant_image_name']}")
    run(f"{CONFIG['elephant_docker']} build --no-cache -t {CONFIG['elephant_image_name']} .")
    if image_id:
        run(f"{CONFIG['elephant_docker']} rmi {image_id}")


"""_summary_
    build the docker image with cache and prune dangling images
"""
def build():
    run(f"{CONFIG['elephant_docker']} build -t {CONFIG['elephant_image_name']} .")
    run(f"{CONFIG['elephant_docker']} image prune -f")        


"""_summary_
    stop the running docker container based on the image name
"""
def stop():
    container_id = subprocess.getoutput(f"{CONFIG['elephant_docker']} ps -aq --filter ancestor={CONFIG['elephant_image_name']}")
    if container_id:
        run(f"{CONFIG['elephant_docker']} stop {container_id}")


"""_summary_
    initialize GPU if available or notify CPU mode
"""
def warmup():
    if CONFIG['elephant_gpu']:
        run(f"{CONFIG['elephant_docker']} run -it --rm --gpus \"device={CONFIG['elephant_gpu']}\" {CONFIG['elephant_image_name']} echo 'warming up GPU...'")
    else:
        print("CPU mode...")


"""_summary_
    launch the application docker container with required ports and environment variables
"""
def launch():
    warmup()
    gpu_arg = f"--gpus \"device={CONFIG['elephant_gpu']}\"" if CONFIG['elephant_gpu'] else ""
    cmd = f"""{CONFIG['elephant_docker']} run -it --rm {gpu_arg} --shm-size=8g -v {CONFIG['elephant_workspace']}:/workspace \
    -p {CONFIG['elephant_http_port']}:{CONFIG['elephant_http_port']} \
    -p {CONFIG['elephant_rabbitmq_node_port']}:{CONFIG['elephant_rabbitmq_node_port']} \
    -p {CONFIG['elephant_rabbitmq_management_port']}:{CONFIG['elephant_rabbitmq_management_port']} \
    -e RABBITMQ_NODENAME=rabbit@localhost \
    -e RABBITMQ_USER={CONFIG['elephant_rabbitmq_user']} \
    -e RABBITMQ_PASSWORD={CONFIG['elephant_rabbitmq_password']} \
    {CONFIG['elephant_image_name']}"""
    run(cmd)


"""_summary_
    open a bash shell inside the container as non-root user
"""
def bash():
    warmup()
    gpu_arg = f"--gpus \"device={CONFIG['elephant_gpu']}\"" if CONFIG['elephant_gpu'] else ""
    cmd = f"""{CONFIG['elephant_docker']} run -it --rm {gpu_arg} --shm-size=8g -v {CONFIG['elephant_workspace']}:/workspace \
    -e AS_LOCAL_USER=1 {CONFIG['elephant_image_name']} /bin/bash"""
    run(cmd)


"""_summary_
    open a bash shell inside the container as root user
"""
def bashroot():
    warmup()
    run(f"{CONFIG['elephant_docker']} run -it --rm --gpus 'device={CONFIG['elephant_gpu']}' --shm-size=8g "
        f"-v {CONFIG['elephant_workspace']}:/workspace "
        f"{CONFIG['elephant_image_name']} /bin/bash", shout=True)


"""_summary_
    launch a Jupyter Notebook inside the container
"""
def notebook():
    warmup()
    gpu_arg = f"--gpus \"device={CONFIG['elephant_gpu']}\"" if CONFIG['elephant_gpu'] else ""
    cmd = f"""{CONFIG['elephant_docker']} run -it --rm {gpu_arg} --shm-size=8g -v {CONFIG['elephant_workspace']}:/workspace \
    --network host -p {CONFIG['elephant_notebook_port']}:{CONFIG['elephant_notebook_port']} \
    {CONFIG['elephant_image_name']} jupyter notebook --no-browser --port={CONFIG['elephant_notebook_port']} --notebook-dir=/workspace"""
    run(cmd)


"""_summary_
    run the docker test build and container
"""
def test():
    run(f"{CONFIG['elephant_docker']} build -t {CONFIG['elephant_image_name']}-test -f Dockerfile-test .")
    run(f"{CONFIG['elephant_docker']} image prune -f")
    run(f"{CONFIG['elephant_docker']} run --rm {CONFIG['elephant_image_name']}-test")


"""_summary_
    display available commands
"""
def help():
    print("""Available commands:
    rebuild     - Rebuild the docker image without cache
    build       - Build the docker image with cache
    stop        - Stop the running container
    warmup      - Initialize the GPU if available
    launch      - Launch the full app container
    bash        - Open a bash shell as non-root user
    bashroot    - Open a bash shell as root user
    notebook    - Launch a Jupyter Notebook
    test        - Build and run docker tests
    """)


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
