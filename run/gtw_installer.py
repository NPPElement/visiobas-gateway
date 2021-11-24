from __future__ import print_function

import argparse
import os
import subprocess
import urllib.request
from pathlib import Path

import pip


def check_root():
    if os.geteuid() != 0:
        exit("Must be run as root.\n")


def message(msg: str):
    print("******************************\n%s\n******************************" % msg)


def run_cmd_with_check(cmd: str):
    code = os.system(cmd)
    if code:
        raise RuntimeError("Return code: %d for `%s`" % (code, cmd))


def run_cmd_with_output(cmd: list[str]):
    return subprocess.run(cmd, capture_output=True).stdout.decode().strip("\n")


def download_file(url, path):
    with urllib.request.urlopen(url) as f:
        path.write_bytes(f.read())
        # response = requests.get(url)
        # if response.status_code == 200:
        #     path.write_bytes(response.content)
        # else:
        #     raise RuntimeError(
        #         "Cannot download `%s` HTTP code: %s"
        #         % (DOCKER_COMPOSE_YAML_PATH, response.status_code)
        #     )


# URLS
GATEWAY_REPOSITORY_URL = "https://github.com/NPPElement/visiobas-gateway"
DOCKER_COMPOSE_YAML_URL = (
    "https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/docker-compose.yaml"
)
ENV_CONFIG_URL = (
    "https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/config/template.env"
)

UNAME_TYPE = run_cmd_with_output(["uname", "-m"])
MACHINE_TYPE = run_cmd_with_output(["dpkg", "--print-architecture"])

# PATHS
INSTALL_DIRECTORY = Path("/opt/visiobas-gateway")
INSTALL_DIRECTORY.mkdir(exist_ok=True)

CONFIG_DIRECTORY = INSTALL_DIRECTORY / "config"
CONFIG_DIRECTORY.mkdir(exist_ok=True)

DOCKER_COMPOSE_YAML_PATH = INSTALL_DIRECTORY / "docker-compose.yaml"
DOCKER_COMPOSE_YAML_ORIGINAL_PATH = INSTALL_DIRECTORY / "docker-compose-original.yaml"
ENV_CONFIG_PATH = CONFIG_DIRECTORY / ".env"

DOCKER_IMAGE = "mtovts/visiobas-gateway:latest"
DOCKER_COMPOSE_GATEWAY_ALIAS = "vb_gateway"
BUILD_CONTEXT = INSTALL_DIRECTORY
DOCKERFILE_NAME = "DOCKERFILE"


class Installer:
    DOCKER_CLIENT_DEPENDENCIES = [
        "apt-transport-https",
        "ca-certificates",
        "curl",
        "gnupg2",
        "software-properties-common",
    ]

    def install(self):
        try:
            run_cmd_with_check("apt-get update -y")

            print("\nInstalling Docker engine\n".upper())
            self.install_docker_engine()

            print("\nInstalling docker-compose\n".upper())
            self.install_docker_compose()

            print("\nAll dependencies installed\n")

            print("\nDownloading `%s`\n" % DOCKER_COMPOSE_YAML_PATH)
            download_file(url=DOCKER_COMPOSE_YAML_URL, path=DOCKER_COMPOSE_YAML_PATH)

            print("\nPulling docker image\n")
            run_cmd_with_check("docker pull %s" % DOCKER_IMAGE)

            print("\nDownloading `%s`\n" % ENV_CONFIG_PATH)
            download_file(url=ENV_CONFIG_URL, path=ENV_CONFIG_PATH)
            message(
                """
                INSTALLATION COMPLETE
                ---------------------
                Please, configure gateway in `%s`. Then run: 
                `python3 /opt/gtw_installer.py -run`
                """
                % CONFIG_DIRECTORY
            )
        except Exception as exc:
            # TODO add traceback
            message(
                """
                INSTALLATION FAILED
                -------------------
                Please contact the VisioBAS Gateway developer and provide this message:
                `%s`
                """
                % exc
            )

    @staticmethod
    def modify_docker_compose_for_build():
        import yaml

        with open(DOCKER_COMPOSE_YAML_PATH, "r") as file:
            docker_compose_dict = yaml.safe_load(file)

        print("\nSaving original `%s`\n" % DOCKER_COMPOSE_YAML_ORIGINAL_PATH)
        with open(DOCKER_COMPOSE_YAML_ORIGINAL_PATH, "w") as file:
            yaml.dump(docker_compose_dict, file)

        service_section = docker_compose_dict["services"][DOCKER_COMPOSE_GATEWAY_ALIAS]
        service_section.pop(["image"])
        service_section["build"] = {
            "context": BUILD_CONTEXT,
            "dockerfile": DOCKERFILE_NAME,
        }
        docker_compose_dict["services"][DOCKER_COMPOSE_GATEWAY_ALIAS] = service_section

        print("\nWriting `%s` for build\n" % DOCKER_COMPOSE_YAML_PATH)
        with open(DOCKER_COMPOSE_YAML_PATH, "w") as file:
            yaml.dump(docker_compose_dict, file)

    def build_gateway_docker_image(self):
        print("\nClone repository to `%s`\n" % INSTALL_DIRECTORY)
        run_cmd_with_check("apt-get install -y git")
        try:
            run_cmd_with_check(
                "git clone %s %s" % (GATEWAY_REPOSITORY_URL, INSTALL_DIRECTORY)
            )
        except RuntimeError:
            run_cmd_with_check("rm -r %s" % INSTALL_DIRECTORY)
            run_cmd_with_check(
                "git clone %s %s" % (GATEWAY_REPOSITORY_URL, INSTALL_DIRECTORY)
            )

        pip.main(["install", "pyyaml"])

        print("\nModifying `%s` for build.\n" % DOCKER_COMPOSE_YAML_PATH)
        self.modify_docker_compose_for_build()

        print("\nBuilding image for VisioBAS Gateway.\n")
        run_cmd_with_check("docker-compose -f %s build" % DOCKER_COMPOSE_YAML_PATH)

    @staticmethod
    def run_gateway(docker_compose_path: Path):
        try:
            run_cmd_with_check("docker-compose -f %s up" % docker_compose_path)
        except RuntimeError:
            message(
                """
                RUN FAILED
                ----------
                Please, try to build docker image with command:
                `python3 /opt/gtw_installer.py -build`
                
                Then run again:
                `python3 /opt/gtw_installer.py -run`
                """
            )

    def install_docker_engine(self):
        cmd = " ".join(("apt-get -y install", *self.DOCKER_CLIENT_DEPENDENCIES))
        run_cmd_with_check(cmd)

        run_cmd_with_check(
            "curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -"
        )
        if UNAME_TYPE == "x86_64":
            run_cmd_with_check(
                'add-apt-repository -y \
                   "deb [arch=amd64] https://download.docker.com/linux/debian \
                   $(lsb_release -cs) \
                   stable"'
            )
        elif MACHINE_TYPE == "armhf":
            run_cmd_with_check(
                'add-apt-repository -y \
                   "deb [arch=armhf] https://download.docker.com/linux/debian \
                   $(lsb_release -cs) \
                   stable"'
            )
        elif MACHINE_TYPE == "arm64":
            run_cmd_with_check(
                'add-apt-repository -y \
                   "deb [arch=arm64] https://download.docker.com/linux/debian \
                   $(lsb_release -cs) \
                   stable"'
            )
        else:
            raise RuntimeError(
                "Could not detect architecture: uname=%s machinery=%s"
                % (UNAME_TYPE, MACHINE_TYPE)
            )
        run_cmd_with_check("apt-get update")
        run_cmd_with_check("apt-get -y install docker-ce-cli")
        run_cmd_with_check("apt install -y docker-ce containerd.io")
        run_cmd_with_check("usermod -aG docker $USER")

    @staticmethod
    def install_docker_compose():
        pip.main(["install", "docker-compose"])


if __name__ == "__main__":
    check_root()

    parser = argparse.ArgumentParser(description="VisioBAS Gateway Installer.")
    parser.add_argument(
        "-install",
        help="Installs Docker Engine, docker-compose, VisioBAS Gateway.",
        action="store_true",  # Default: False
    )
    parser.add_argument(
        "-build",
        help="Builds VisioBAS Gateway docker image.",
        action="store_true",  # Default: False
    )
    parser.add_argument(
        "-run",
        help="Runs VisioBAS Gateway.",
        action="store_true",  # Default: False
    )
    args = parser.parse_args()

    installer = Installer()

    if args.install:
        installer.install()
    elif args.build:
        installer.build_gateway_docker_image()
    elif args.run:
        installer.run_gateway(docker_compose_path=DOCKER_COMPOSE_YAML_PATH)
    else:
        exit("Please provide command to run: `-install` | `-build` | `-run`.")
