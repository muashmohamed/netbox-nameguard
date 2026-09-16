from netbox.plugins import PluginConfig


class NameGuardConfig(PluginConfig):
    name = "netbox_nameguard"
    verbose_name = "NameGuard"
    description = "Standardize and enforce device naming conventions across the inventory."
    version = "0.1.0"
    author = "Your Name"
    base_url = "nameguard"
    min_version = "4.5.0"
    default_settings = {
        # Default zero-padded width for the {SEQ} token, used when a
        # NamingPattern doesn't override it.
        "default_seq_width": 3,
    }


config = NameGuardConfig
