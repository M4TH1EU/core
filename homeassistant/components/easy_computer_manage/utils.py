import logging

import fabric2
from fabric2 import Connection

_LOGGER = logging.getLogger(__name__)
# _LOGGER.setLevel(logging.DEBUG)


def create_ssh_connection(host: str, username: str, password: str, port=22):
    conf = fabric2.Config()
    conf.run.hide = True
    conf.run.warn = True
    conf.warn = True
    connection = Connection(
        host=host, user=username, port=port, connect_timeout=3, connect_kwargs={"password": password},
        config=conf
    )

    connection.config.sudo.password = password
    _LOGGER.info("CONNECTED SSH")

    return connection


def is_unix_system(connection: Connection):
    return get_operating_system(connection) == "Linux/Unix"


def get_operating_system_version(connection: Connection, is_unix=None):
    if is_unix is None:
        is_unix = is_unix_system(connection)

    if is_unix:
        return connection.run(
            "lsb_release -a | awk '/Description/ {print $2, $3, $4}'"
        ).stdout
    else:
        return connection.run(
            'for /f "tokens=2" %i in (\'systeminfo ^| find "OS Name"\') do @echo %i'
        )


def get_operating_system(connection: Connection):
    result = connection.run("uname")
    if result.return_code == 0:
        return "Linux/Unix"
    else:
        return "Windows/Other"


def shutdown_system(connection: Connection, is_unix=None):
    if is_unix is None:
        is_unix = is_unix_system(connection)

    if is_unix:
        # First method using shutdown command
        result = connection.sudo("shutdown -h now")
        if result.return_code != 0:
            # Try a second method using init command
            result = connection.sudo("init 0")
            if result.return_code != 0:
                # Try a third method using systemctl command
                result = connection.sudo("systemctl poweroff")
                if result.return_code != 0:
                    _LOGGER.error("Cannot restart system, all methods failed.")
    else:
        # First method using shutdown command
        result = connection.run("shutdown /s /t 0")
        if result.return_code != 0:
            # Try a second method using init command
            result = connection.run("wmic os where Primary=TRUE call Shutdown")
            if result.return_code != 0:
                _LOGGER.error("Cannot restart system, all methods failed.")


def restart_system(connection: Connection, is_unix=None):
    if is_unix is None:
        is_unix = is_unix_system(connection)

    if is_unix:
        # First method using shutdown command
        result = connection.sudo("shutdown -r now")
        if result.return_code != 0:
            # Try a second method using init command
            result = connection.sudo("init 6")
            if result.return_code != 0:
                # Try a third method using systemctl command
                result = connection.sudo("systemctl reboot")
                if result.return_code != 0:
                    _LOGGER.error("Cannot restart system, all methods failed.")
    else:
        # First method using shutdown command
        result = connection.run("shutdown /r /t 0")
        if result.return_code != 0:
            # Try a second method using wmic command
            result = connection.run("wmic os where Primary=TRUE call Reboot")
            if result.return_code != 0:
                _LOGGER.error("Cannot restart system, all methods failed.")


def sleep_system(connection: Connection, is_unix=None):
    if is_unix is None:
        is_unix = is_unix_system(connection)

    if is_unix:
        # First method using systemctl command
        result = connection.sudo("systemctl suspend")
        if result.return_code != 0:
            # Try a second method using pm-suspend command
            result = connection.sudo("pm-suspend")
            if result.return_code != 0:
                _LOGGER.error("Cannot restart system, all methods failed.")
    else:
        # First method using shutdown command
        result = connection.run("shutdown /h /t 0")
        if result.return_code != 0:
            # Try a second method using rundll32 command
            result = connection.run("rundll32.exe powrprof.dll,SetSuspendState Sleep")
            if result.return_code != 0:
                _LOGGER.error("Cannot restart system, all methods failed.")


def get_windows_entry_in_grub(connection: Connection):
    result = connection.sudo("awk -F \"'\" '/windows/ {print $2}' /boot/grub/grub.cfg")

    if result.return_code == 0:
        _LOGGER.debug("Found Windows entry in grub : " + result.stdout.strip())
    else:
        result = connection.sudo("awk -F \"'\" '/windows/ {print $2}' /boot/grub2/grub.cfg")
        if result.return_code == 0:
            _LOGGER.debug("Found windows entry in grub2 : " + result.stdout.strip())
        else:
            _LOGGER.error("Cannot find windows entry in grub")
            return None

    # Check if the entry is valid
    if result.stdout.strip() != "":
        return result.stdout.strip()
    else:
        _LOGGER.error("Cannot find windows entry in grub")
        return None


def restart_to_windows_from_linux(connection: Connection):
    if is_unix_system(connection):
        windows_entry = get_windows_entry_in_grub(connection)
        if windows_entry is not None:
            # First method using grub-reboot command
            result = connection.sudo(f"grub-reboot \"{windows_entry}\"")

            if result.return_code != 0:
                # Try a second method using grub2-reboot command
                result = connection.sudo(f"grub2-reboot \"{windows_entry}\"")

            # Restart system if successful grub(2)-reboot command
            if result.return_code == 0:
                _LOGGER.info("Rebooting to Windows")
                restart_system(connection)
            else:
                _LOGGER.error("Cannot restart system to windows from linux, all methods failed.")
    else:
        _LOGGER.error("Cannot restart to Windows from Linux, system is not Linux/Unix")
