from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

atolltype_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:atolltype_add", title="Add", icon_class="mdi mdi-plus-thick"),
]
islandtype_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:islandtype_add", title="Add", icon_class="mdi mdi-plus-thick"),
]
facilitytype_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:facilitytype_add", title="Add", icon_class="mdi mdi-plus-thick"),
]
sitecode_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:sitecode_add", title="Add", icon_class="mdi mdi-plus-thick"),
]
pattern_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:namingpattern_add", title="Add", icon_class="mdi mdi-plus-thick"),
]
rack_pattern_buttons = [
    PluginMenuButton(link="plugins:netbox_nameguard:racknamingpattern_add", title="Add", icon_class="mdi mdi-plus-thick"),
]

menu = PluginMenu(
    label="NameGuard",
    icon_class="mdi mdi-tag-check-outline",
    groups=(
        ("Glossary", (
            PluginMenuItem(
                link="plugins:netbox_nameguard:atolltype_list",
                link_text="Atoll Types",
                buttons=atolltype_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_nameguard:islandtype_list",
                link_text="Island Types",
                buttons=islandtype_buttons,
            ),
            PluginMenuItem(
                link="plugins:netbox_nameguard:facilitytype_list",
                link_text="Facility Types",
                buttons=facilitytype_buttons,
            ),
        )),
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
            PluginMenuItem(
                link="plugins:netbox_nameguard:racknamingpattern_list",
                link_text="Rack Naming Patterns",
                buttons=rack_pattern_buttons,
            ),
        )),
        ("Enforcement", (
            PluginMenuItem(
                link="plugins:netbox_nameguard:compliance_list",
                link_text="Compliance Dashboard",
            ),
            PluginMenuItem(
                link="plugins:netbox_nameguard:rack_compliance_list",
                link_text="Rack Compliance",
            ),
            PluginMenuItem(
                link="plugins:netbox_nameguard:renamelog_list",
                link_text="Rename Log",
            ),
        )),
    ),
)
