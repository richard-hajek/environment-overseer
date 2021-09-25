class STATUS:
    ENABLED = "enabled"  # Enabled
    DISABLED = "disabled"  # Disabled
    READY = "ready"  # Enabled - y
    INTERRUPTED = "interrupted"  # Disabled - y
    FORCED = "forced"  # Enabled - y

    base = {
        ENABLED: ENABLED,
        READY: ENABLED,
        FORCED: ENABLED,
        DISABLED: DISABLED,
        INTERRUPTED: DISABLED
    }


class ACTION:
    IDLE = "idle"
    ENABLE = "enable"
    DISABLE = "disable"
    INTERRUPT = "interrupt"
    FORCE = "force"


exit_codes = {
    "success": (0, "Success"),
    "daemon_running": (1, "Daemon is running"),
    "daemon_not_running": (2, "Daemon is not running"),
    "root": (3, "Must be ran as root"),
    "misconfiguration": (4, "Overseer is misconfigured")
}


def die(reason):
    print(exit_codes[reason][1])
    exit(exit_codes[reason][0])


reset_phrase = "I am an addicted idiot and need to reset the trackers."
phrase_override_env = "OVERSEER_PHRASE_OVERRIDE"

path_home = "/etc/overseer"

path_activities = f"{path_home}/activities"
path_activity_status = f"{path_home}/status"
path_checks = f"{path_home}/checks"
path_trackers = f"{path_home}/trackers"
path_reverse_trackers = f"{path_home}/reverse"
path_continuous = f"{path_home}/continuous"
path_interrupts = f"{path_home}/interrupts"

path_scripts_enable = f"{path_home}/scripts/enable"
path_scripts_disable = f"{path_home}/scripts/disable"
path_scripts_dual = f"{path_home}/scripts/dual"
path_scripts_managers = f"{path_home}/scripts/managers"
path_scripts_checks = f"{path_home}/scripts/checks"
path_scripts_extensions = f"{path_home}/scripts/extensions"

path_helpers = f"{path_home}/scripts/helpers"

path_tmp = f"/tmp/overseer"

directories = [path_home, path_activities, path_activity_status, path_trackers, path_reverse_trackers, path_checks,
               path_continuous, path_interrupts, path_scripts_enable, path_scripts_disable,
               path_scripts_managers, path_scripts_checks, path_scripts_extensions, path_helpers, path_tmp,
               path_scripts_dual]
