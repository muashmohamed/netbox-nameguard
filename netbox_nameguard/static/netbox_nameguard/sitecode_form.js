/*
 * SiteCode add/edit form: Site and Location are mutually exclusive
 * (a SiteCode targets exactly one of them). Rather than letting the
 * user pick both and only finding out from a server-side error after
 * submitting, disable whichever field isn't in use as soon as the
 * other one gets a value. location_kind only makes sense when Location
 * is the target, so it's disabled (and cleared) whenever Site is chosen.
 */
(function ($) {
    $(function () {
        var $site = $('#id_site');
        var $location = $('#id_location');
        var $locationKind = $('input[name="location_kind"]');

        if (!$site.length || !$location.length) {
            return;  // not on the SiteCode form, nothing to do
        }

        function clearAndDisable($field) {
            $field.val(null).trigger('change');
            $field.prop('disabled', true);
        }

        function refreshLocationKind() {
            if ($location.val()) {
                $locationKind.prop('disabled', false);
            } else {
                $locationKind.prop('checked', false).prop('disabled', true);
            }
        }

        function refresh() {
            if ($site.val()) {
                clearAndDisable($location);
            } else if ($location.val()) {
                clearAndDisable($site);
            } else {
                $site.prop('disabled', false);
                $location.prop('disabled', false);
            }
            refreshLocationKind();
        }

        $site.on('change', function () {
            if ($(this).val()) {
                clearAndDisable($location);
            } else {
                $location.prop('disabled', false);
            }
            refreshLocationKind();
        });

        $location.on('change', function () {
            if ($(this).val()) {
                clearAndDisable($site);
            } else {
                $site.prop('disabled', false);
            }
            refreshLocationKind();
        });

        // Reflect whichever value is already set when editing an existing SiteCode.
        refresh();
    });
})(django.jQuery || jQuery);
