import logging

from fabric2 import Connection

_LOGGER = logging.getLogger(__name__)


def create_ssh_connection(host: str, username: str, password: str, port=22):
    connection = Connection(
        host=host, user=username, port=port, connect_kwargs={"password": password}
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


def get_unix_system_grub_os_list(connection: Connection):
    result = connection.sudo("cat /boot/grub/grub.cfg | grep menuentry")
    if result.return_code == 0:
        return result.stdout.splitlines()
    else:
        result = connection.sudo("cat /boot/grub2/grub.cfg | grep menuentry")
        if result.return_code == 0:
            return result.stdout.splitlines()

        _LOGGER.error("Cannot get grub os list")


def restart_to_windows_from_linux(connection: Connection):
    if is_unix_system(connection):
        # sudo grub-reboot "$(grep -i windows /boot/grub/grub.cfg|cut -d"'" -f2)" && sudo reboot
        result = connection.sudo(
            'grub-reboot "$(grep -i windows /boot/grub/grub.cfg|cut -d"\'" -f2)"'
        )

        # we try with grub2 if grub command failed
        if result.return_code != 0:
            result = connection.sudo(
                'grub2-reboot "$(grep -i windows /boot/grub/grub.cfg|cut -d"\'" -f2)"'
            )

        # grub reboot success, we reboot the system
        if result.return_code == 0:
            restart_system(connection)
        else:
            _LOGGER.error(
                "Cannot restart system to windows from linux, all methods failed."
            )
    else:
        _LOGGER.error("Cannot restart to Windows from Linux, system is not Linux/Unix")
