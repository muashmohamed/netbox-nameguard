(function ($) {
    $(function () {
        var $site = $('#id_site');
        var $location = $('#id_location');

        if (!$site.length || !$location.length) {
            return;
        }

        function clearAndDisable($field) {
            $field.val(null).trigger('change');
            $field.prop('disabled', true);
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
        }

        $site.on('change', function () {
            if ($(this).val()) {
                clearAndDisable($location);
            } else {
                $location.prop('disabled', false);
            }
        });

        $location.on('change', function () {
            if ($(this).val()) {
                clearAndDisable($site);
            } else {
                $site.prop('disabled', false);
            }
        });

        refresh();
    });
})(django.jQuery || jQuery);
