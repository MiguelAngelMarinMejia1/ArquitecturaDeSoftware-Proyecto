/* Hotel MDJ: small progressive enhancements. The site works without them. */

(function () {
    "use strict";

    /* Date pairs (check-in / check-out). The check-out can never be on or
       before the check-in: its minimum follows the chosen check-in, and a
       check-out left behind is moved to the next day. The server still
       validates the range; this only saves the guest a round trip. */
    function nextDay(isoDate) {
        var d = new Date(isoDate + "T00:00:00");
        d.setDate(d.getDate() + 1);
        var month = String(d.getMonth() + 1).padStart(2, "0");
        var day = String(d.getDate()).padStart(2, "0");
        return d.getFullYear() + "-" + month + "-" + day;
    }

    document.querySelectorAll("form").forEach(function (form) {
        var checkIn = form.querySelector('input[name="check_in"][type="date"]');
        var checkOut = form.querySelector('input[name="check_out"][type="date"]');
        if (!checkIn || !checkOut) return;

        function sync() {
            if (!checkIn.value) return;
            var minimum = nextDay(checkIn.value);
            checkOut.min = minimum;
            if (!checkOut.value || checkOut.value < minimum) checkOut.value = minimum;
        }

        checkIn.addEventListener("change", sync);
        if (checkIn.value) checkOut.min = nextDay(checkIn.value);
    });

    /* Only one "Book" on screen: the header button fades out while the
       hero's own call to action is visible. Without IntersectionObserver
       (or on pages with no hero) the header button simply stays. */
    var heroCta = document.querySelector('[data-role="hero-cta"]');
    var headerCta = document.querySelector('[data-role="header-cta"]');
    if (heroCta && headerCta && "IntersectionObserver" in window) {
        new IntersectionObserver(function (entries) {
            headerCta.classList.toggle("is-hidden", entries[0].isIntersecting);
        }, { rootMargin: "-80px 0px 0px 0px" }).observe(heroCta);
    }

    /* Avoid double bookings from a double click: once a POST form is sent,
       its submit button is disabled and says what is happening. */
    document.querySelectorAll('form[method="post"]').forEach(function (form) {
        form.addEventListener("submit", function () {
            var button = form.querySelector('button[type="submit"]');
            if (!button || button.disabled) return;
            window.setTimeout(function () {
                button.disabled = true;
                button.setAttribute("aria-busy", "true");
                if (button.dataset.busyLabel) button.textContent = button.dataset.busyLabel;
            }, 0);
        });
    });
})();
