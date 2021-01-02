from os import environ


def read_cfg_from_env() -> dict:
    """
    :return: Config, read from environment variables
    """
    try:
        config = {
            'http': {
                'get_host': environ['HTTP_GET_HOST'],
                'post_hosts': [host.strip("'") for host in
                               environ.get('HTTP_POST_HOSTS', '').split(' ')],  # todo
                'port': int(environ.get('HTTP_PORT', 8080)),
                'auth': {
                    'login': environ['HTTP_AUTH_LOGIN'],
                    'password': environ['HTTP_AUTH_PASSWORD']
                }
            },
            'bacnet_verifier': {
                'http_enable': True if environ.get(
                    'HTTP_ENABLE').lower() == 'true' else False,
                'mqtt_enable': True if environ.get(
                    'MQTT_ENABLE').lower() == 'true' else False,
            },
            'bacnet': {
                'default_update_period': int(
                    environ.get('BACNET_DEFAULT_UPDATE_PERIOD', 10)),
                'interfaces': environ.get('BACNET_INTERFACES', '').split()
            },
            'modbus': {
                'default_update_period': int(
                    environ.get('MODBUS_DEFAULT_UPDATE_PERIOD', 10))
            }
        }
    except KeyError:
        raise ValueError(
            "Please ensure environment variables are set to: \n"
            "'HTTP_GET_HOST'\n'HTTP_POST_HOSTS'\n"
            "'HTTP_AUTH_LOGIN'\n'HTTP_AUTH_PASSWORD'\n\n"
            "Also you can provide optional variables: \n"
            "'HTTP_PORT' by default = 8080\n"
            "'HTTP_ENABLE' by default = FALSE\n"
            "'MQTT_ENABLE' by default = FALSE\n"
            "'BACNET_DEFAULT_UPDATE_PERIOD' by default = 10\n"
            "'MODBUS_DEFAULT_UPDATE_PERIOD' by default = 10\n"
        )
    else:
        return config
