from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

sitecode_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:sitecode_add", title="Add", icon_class="mdi mdi-plus-thick"),
]
pattern_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:namingpattern_add", title="Add", icon_class="mdi mdi-plus-thick"),
]

menu = PluginMenu(
    label="NameGuard",
    icon_class="mdi mdi-tag-check-outline",
    groups=(
        ("Naming Rules", (
            PluginMenuItem(
                link="plugins:netbox_nameguard:sitecode_list",
                link_text="Site Codes",
                buttons=sitecode_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_nameguard:namingpattern_list",
                link_text="Naming Patterns",
                buttons=pattern_buttons,
            ),
        )),
        ("Enforcement", (
            PluginMenuItem(
                link="plugins:netbox_nameguard:compliance_list",
                link_text="Compliance Dashboard",
            ),
            PluginMenuItem(
                link="plugins:netbox_nameguard:renamelog_list",
                link_text="Rename Log",
            ),
        )),
    ),
)
