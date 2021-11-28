from __future__ import print_function

import argparse
import os
import subprocess
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path

import pip


def run_cmd_with_output(cmd: list[str]):
    return subprocess.run(cmd, capture_output=True).stdout.decode().strip("\n")


# URLS
GATEWAY_REPOSITORY_URL = "https://github.com/NPPElement/visiobas-gateway"
ENV_TEMPLATE_URL = "https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/config/template.env"  # noqa

UNAME_TYPE = run_cmd_with_output(["uname", "-m"])
MACHINE_TYPE = run_cmd_with_output(["dpkg", "--print-architecture"])

# PATHS
INSTALL_DIRECTORY = Path("/opt/visiobas-gateway")
INSTALL_DIRECTORY.mkdir(exist_ok=True)
CONFIG_DIRECTORY = INSTALL_DIRECTORY / "config"
CONFIG_DIRECTORY.mkdir(exist_ok=True)
ENV_CONFIG_PATH = CONFIG_DIRECTORY / ".env"

# COMMANDS
CMD_DOCKER_INSTALL = "--docker-install"
CMD_DOCKER_BUILD_IMAGE = "--docker-build-image"
CMD_DOCKER_RUN = "--docker-run"
CMD_INSTALL = "--install"
CMD_RUN = "--run"


def check_root() -> None:
    if os.geteuid() != 0:
        exit("Must be run as root.\n")


def message_framed(msg: str) -> None:
    print("\n******************************\n%s\n******************************\n" % msg)


def run_cmd_with_check(cmd: str) -> None:
    code = os.system(cmd)
    if code:
        raise RuntimeError("Return code: %d for `%s`" % (code, cmd))


def download_file(url: str, path: Path) -> None:
    with urllib.request.urlopen(url) as file:
        path.write_bytes(file.read())


def git_clone() -> None:
    run_cmd_with_check("apt-get install -y git gcc")

    print("\nRemoving existing `%s`\n" % INSTALL_DIRECTORY)
    run_cmd_with_check("rm -r %s" % INSTALL_DIRECTORY)

    print("\nCloning repository to `%s`\n" % INSTALL_DIRECTORY)
    run_cmd_with_check("git clone %s %s" % (GATEWAY_REPOSITORY_URL, INSTALL_DIRECTORY))


class AbstractInstaller(ABC):
    @abstractmethod
    def install(self) -> None:
        pass

    @abstractmethod
    def run_gateway(self) -> None:
        pass


class InstallWithDocker(AbstractInstaller):
    DOCKER_CLIENT_DEPENDENCIES = [
        "apt-transport-https",
        "ca-certificates",
        "curl",
        "gnupg2",
        "software-properties-common",
    ]
    DOCKER_COMPOSE_YAML_URL = "https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/docker-compose.yaml"  # noqa
    DOCKER_COMPOSE_YAML_NAME = "docker-compose.yaml"
    DOCKER_COMPOSE_YAML_PATH = INSTALL_DIRECTORY / DOCKER_COMPOSE_YAML_NAME
    DOCKER_COMPOSE_YAML_ORIGINAL_PATH = INSTALL_DIRECTORY / "docker-compose-original.yaml"

    DOCKER_IMAGE = "mtovts/visiobas-gateway:latest"
    DOCKER_COMPOSE_GATEWAY_ALIAS = "vb_gateway"
    BUILD_CONTEXT = INSTALL_DIRECTORY

    def install(self) -> None:
        try:
            print("\nInstalling Docker engine\n")
            self.install_docker_engine()

            print("\nInstalling docker-compose\n")
            self.install_docker_compose()

            print("\nDownloading `%s`\n" % self.DOCKER_COMPOSE_YAML_PATH)
            download_file(
                url=self.DOCKER_COMPOSE_YAML_URL, path=self.DOCKER_COMPOSE_YAML_PATH
            )

            # print("\nPulling docker image\n")
            # run_cmd_with_check("docker pull %s" % self.DOCKER_IMAGE)

            print("\nDownloading `%s`\n" % ENV_CONFIG_PATH)
            download_file(url=ENV_TEMPLATE_URL, path=ENV_CONFIG_PATH)
            message_framed(
                """
                INSTALLATION COMPLETE
                ---------------------
                Please, configure gateway in `%s`. 
                
                Then run: 
                `python3 %s %s`
                """
                % (ENV_CONFIG_PATH, __file__, CMD_DOCKER_RUN)
            )
        except Exception as exc:
            message_framed(
                """
                INSTALLATION FAILED
                -------------------
                Please contact the VisioBAS Gateway developer and provide this message:
                `%s`
                """
                % exc
            )

    def install_docker_engine(self) -> None:
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
    def install_docker_compose() -> None:
        pip.main(["install", "docker-compose"])

    def _modify_docker_compose_for_build(self) -> None:
        pip.main(["install", "pyyaml"])
        import yaml

        with open(self.DOCKER_COMPOSE_YAML_PATH, "r") as file:
            docker_compose_dict = yaml.safe_load(file)

        print("\nSaving original to `%s`\n" % self.DOCKER_COMPOSE_YAML_ORIGINAL_PATH)
        with open(self.DOCKER_COMPOSE_YAML_ORIGINAL_PATH, "w") as file:
            yaml.dump(docker_compose_dict, file)

        service_section = docker_compose_dict["services"][self.DOCKER_COMPOSE_GATEWAY_ALIAS]
        service_section.pop("image")  # Removing image
        service_section["build"] = {
            "context": str(self.BUILD_CONTEXT),
            "dockerfile": "Dockerfile",
        }  # Add build
        docker_compose_dict["services"][self.DOCKER_COMPOSE_GATEWAY_ALIAS] = service_section

        print("\nWriting `%s` for build\n" % self.DOCKER_COMPOSE_YAML_PATH)
        with open(self.DOCKER_COMPOSE_YAML_PATH, "w") as file:
            yaml.dump(docker_compose_dict, file, encoding="UTF-8")

    def build_docker_image(self) -> None:
        git_clone()

        print("\nModifying `%s` for build.\n" % self.DOCKER_COMPOSE_YAML_PATH)
        self._modify_docker_compose_for_build()

        run_cmd_with_check(
            "docker build -t mtovts/visiobas-gateway:latest %s" % INSTALL_DIRECTORY
        )

        message_framed(
            """
            DOCKER IMAGE BUILT
            ------------------
            Please, configure gateway in `%s`.
            
            Then run: 
            `python3 %s %s`
            """
            % (ENV_CONFIG_PATH, __file__, CMD_DOCKER_RUN)
        )

    def run_gateway(self) -> None:
        try:
            run_cmd_with_check("docker-compose -f %s up" % self.DOCKER_COMPOSE_YAML_PATH)
        except RuntimeError:
            message_framed(
                """
                RUN FAILED
                ----------
                Please, try to build docker image with command:
                `python3 %s %s`

                Then run again:
                `python3 %s %s`
                """
                % (__file__, CMD_DOCKER_BUILD_IMAGE, __file__, CMD_DOCKER_RUN)
            )


class Installer(AbstractInstaller):
    def install(self) -> None:
        run_cmd_with_check("apt-get update && apt-get install -y iputils-ping")

        print("\nInstalling Poetry\n")
        self._install_poetry()

        git_clone()

        # Poetry not support target directory now.
        run_cmd_with_check("cd %s && poetry install --no-dev" % INSTALL_DIRECTORY)

    @staticmethod
    def _install_poetry() -> None:
        run_cmd_with_check(
            r"curl -sSL https://install.python-poetry.org "
            r"| POETRY_HOME=/opt/poetry python3 && "
            r"\ cd /usr/local/bin && "
            r"\ ln -s /opt/poetry/bin/poetry"
        )

    def run_gateway(self) -> None:
        run_cmd_with_check(
            "systemctl enable %s/run/visiobas_gateway.service" % INSTALL_DIRECTORY
        )
        run_cmd_with_check(
            "systemctl restart %s/run/visiobas_gateway.service" % INSTALL_DIRECTORY
        )
        # run_cmd_with_check("python3 %s/visiobas_gateway" % INSTALL_DIRECTORY)


if __name__ == "__main__":
    check_root()

    ARGS = (
        # Commands with Docker.
        (
            CMD_DOCKER_INSTALL,
            "Installs Docker Engine, docker-compose, VisioBAS Gateway.",
        ),
        (CMD_DOCKER_BUILD_IMAGE, "Builds VisioBAS Gateway docker image."),
        (CMD_DOCKER_RUN, "Runs VisioBAS Gateway in docker."),
        # Commands without Docker.
        (CMD_INSTALL, "Installs VisioBAS Gateway without Docker."),
        (CMD_RUN, "Runs VisioBAS Gateway."),
    )
    parser = argparse.ArgumentParser(description="VisioBAS Gateway Installer.")
    for arg, description in ARGS:
        parser.add_argument(arg, help=description, action="store_true")
    args = parser.parse_args()

    # Commands with Docker.
    if args.docker_install:
        InstallWithDocker().install()
    elif args.docker_build_image:
        InstallWithDocker().build_docker_image()
    elif args.docker_run:
        InstallWithDocker().run_gateway()

    # Commands without Docker.
    elif args.install:
        Installer().install()
    elif args.run:
        Installer().run_gateway()

    else:
        exit("Please provide command to run: %s." % args)
