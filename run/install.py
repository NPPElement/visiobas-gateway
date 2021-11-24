from __future__ import print_function

import urllib.request
from pathlib import Path

import pip

from run import check_root, message, run_cmd_with_check, run_cmd_with_output

UNAME_TYPE = run_cmd_with_output(["uname", "-m"])
MACHINE_TYPE = run_cmd_with_output(["dpkg", "--print-architecture"])

INSTALL_DIRECTORY = Path("/opt/visiobas-gateway")
INSTALL_DIRECTORY.mkdir(exist_ok=True)

CONFIG_DIRECTORY = INSTALL_DIRECTORY / "config"
CONFIG_DIRECTORY.mkdir(exist_ok=True)

DOCKER_COMPOSE_YAML_URL = (
    "https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/docker-compose.yaml"
)
DOCKER_COMPOSE_YAML_PATH = INSTALL_DIRECTORY / "docker-compose.yaml"

ENV_CONFIG_URL = (
    "https://raw.githubusercontent.com/NPPElement/visiobas-gateway/main/config/template.env"
)
ENV_CONFIG_PATH = CONFIG_DIRECTORY / ".env"

DOCKER_IMAGE = "mtovts/visiobas-gateway:latest"


class Installer:
    DOCKER_CLIENT_DEPENDENCIES = [
        "apt-transport-https",
        "ca-certificates",
        "curl",
        "gnupg2",
        "software-properties-common",
    ]

    @staticmethod
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

    def install_docker_engine(self):
        """
        Returns:
            Is installed successful.
        Raises:
            RuntimeError if return code any of cmd is not 0.
        """

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

    installer = Installer()
    try:
        run_cmd_with_check("apt-get update -y")

        print("\nInstalling Docker engine\n".upper())
        installer.install_docker_engine()

        print("\nInstalling docker-compose\n".upper())
        installer.install_docker_compose()

        print("\nAll dependencies installed\n")

        print("\nDownloading `%s`\n" % DOCKER_COMPOSE_YAML_PATH)
        installer.download_file(
            url=DOCKER_COMPOSE_YAML_URL,
            path=DOCKER_COMPOSE_YAML_PATH,
        )

        print("\nPulling docker image\n")
        run_cmd_with_check("docker pull %s" % DOCKER_IMAGE)

        print("\nDownloading `%s`\n" % ENV_CONFIG_PATH)
        installer.download_file(
            url=ENV_CONFIG_URL,
            path=ENV_CONFIG_PATH,
        )
        message(
            """
            INSTALLATION COMPLETE
            ---------------------
            Please, configure gateway in `%s`
            Then run `python3 /opt/visiobas-gateway/run/start.py`
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
            %s
            """
            % exc
        )
