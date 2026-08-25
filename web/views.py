"""Server-rendered pages for Hotel MDJ.

These views share their business core with the JSON API: both call the same
``ReservationService``. Nothing here calculates a price, checks availability or
decides whether a booking is valid -- a view reads the request, delegates, and
renders.

Where the data travels
----------------------
Search criteria (dates, occupancy) ride in the query string: they identify no
one, and keeping them in the URL makes a set of results shareable and
reloadable. Guest details only ever travel in a POST body, because URLs are
retained in browser history, web server and proxy logs, and are leaked to third
parties through the ``Referer`` header.

The booking wizard
------------------
Booking runs as three steps that share one route. Which step renders is derived
from what the URL already carries -- dates, then chosen rooms -- so no step is
stored on the server. That keeps the browser's back button, a refresh and a
pasted link all working, and it is why a guest who returns to a URL sees exactly
the step they left.

``step`` is the one exception: it lets a guest move *backwards* to correct
something without losing what they had already chosen.
"""

from datetime import date, datetime

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View

from reservation.domain.exceptions import ReservationDomainError
from reservation.models import Payment, Room
from reservation.selectors import available_rooms, room_types_catalog
from reservation.services import ReservationService

SESSION_RECENT_RESERVATION = "recent_reservation_code"


def _parse_date(raw):
    """Read an ISO date from the query string, ignoring anything malformed."""
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


class SearchCriteriaMixin:
    """Extracts and normalises the availability criteria from a request."""

    @staticmethod
    def read_criteria(request):
        check_in = _parse_date(request.GET.get("check_in"))
        check_out = _parse_date(request.GET.get("check_out"))

        def positive_int(name, default):
            try:
                return max(int(request.GET.get(name, default)), 0)
            except (TypeError, ValueError):
                return default

        return {
            "check_in": check_in,
            "check_out": check_out,
            "adults": positive_int("adults", 1) or 1,
            "children": positive_int("children", 0),
            "rooms_wanted": positive_int("rooms", 1) or 1,
            "is_complete": bool(check_in and check_out and check_out > check_in),
        }


class HomeView(SearchCriteriaMixin, View):
    """Landing page: introduces the hotel and funnels visitors into booking."""

    template_name = "web/home.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "room_types": room_types_catalog(),
                "today": date.today().isoformat(),
            },
        )


class ReservationPageView(SearchCriteriaMixin, View):
    """The booking funnel: choose dates, choose a room, fill in details.

    Only one step is on screen at a time. Stacking all three made the page long
    enough that every reload dropped the guest back at the top, far above
    whatever they had just done.
    """

    template_name = "web/reservations.html"

    STEP_DATES = 1
    STEP_ROOMS = 2
    STEP_DETAILS = 3

    BACK_TARGETS = {"dates": STEP_DATES, "rooms": STEP_ROOMS}

    def get(self, request):
        criteria = self.read_criteria(request)
        selected_ids = [
            int(value) for value in request.GET.getlist("room") if value.isdigit()
        ]
        step = self._resolve_step(criteria, selected_ids, request.GET.get("step"))

        context = {
            "criteria": criteria,
            "step": step,
            "today": date.today().isoformat(),
            "payment_methods": Payment.Method.choices,
            "url_step_dates": self._url_for_step(request, "dates"),
            "url_step_rooms": self._url_for_step(request, "rooms"),
        }

        if criteria["is_complete"]:
            context["guests"] = criteria["adults"] + criteria["children"]
            context["nights"] = (criteria["check_out"] - criteria["check_in"]).days

        if step == self.STEP_ROOMS:
            context["results"] = available_rooms(
                check_in=criteria["check_in"],
                check_out=criteria["check_out"],
                guests=None,
            )
            context["selected_ids"] = selected_ids

        if step == self.STEP_DETAILS:
            selected = list(
                Room.objects.filter(pk__in=selected_ids).select_related("room_type")
            )
            context["selected_rooms"] = selected
            context["quote"] = ReservationService().quote(
                selected, criteria["check_in"], criteria["check_out"]
            )

        return render(request, self.template_name, context)

    def _resolve_step(self, criteria, selected_ids, requested):
        """Derive the step from the data, letting ``step`` only move backwards.

        Reading it this way means a guest can never land on a step whose inputs
        are missing, however the URL was assembled.
        """
        if not criteria["is_complete"]:
            return self.STEP_DATES

        furthest = self.STEP_DETAILS if selected_ids else self.STEP_ROOMS
        return min(self.BACK_TARGETS.get(requested, furthest), furthest)

    @staticmethod
    def _url_for_step(request, step):
        """Link back to an earlier step carrying everything chosen so far."""
        params = request.GET.copy()
        params["step"] = step
        return f"{reverse('web:reservations')}?{params.urlencode()}"

    def post(self, request):
        criteria_qs = request.POST.get("criteria_query", "")
        payload = {
            "check_in_date": _parse_date(request.POST.get("check_in")),
            "check_out_date": _parse_date(request.POST.get("check_out")),
            "room_ids": [
                int(value)
                for value in request.POST.getlist("room")
                if value.isdigit()
            ],
            "num_adults": int(request.POST.get("adults") or 1),
            "num_children": int(request.POST.get("children") or 0),
            "special_requests": request.POST.get("special_requests", ""),
            "first_name": request.POST.get("first_name", ""),
            "last_name": request.POST.get("last_name", ""),
            "email": request.POST.get("email", ""),
            "phone": request.POST.get("phone", ""),
            "country": request.POST.get("country", ""),
            "marketing_consent": bool(request.POST.get("marketing_consent")),
            "payment_method": request.POST.get(
                "payment_method", Payment.Method.CREDIT_CARD
            ),
        }

        try:
            reservation = ReservationService().create_reservation(payload)
        except ReservationDomainError as exc:
            messages.error(request, str(exc))
            back = reverse("web:reservations")
            return redirect(f"{back}?{criteria_qs}" if criteria_qs else back)

        # Post/Redirect/Get: a refresh on the confirmation page must not create
        # a second booking.
        request.session[SESSION_RECENT_RESERVATION] = reservation.confirmation_code
        return redirect(
            "web:reservation-confirmation", code=reservation.confirmation_code
        )


class ReservationConfirmationView(View):
    """Shows a booking immediately after it was made.

    Access is granted by a token left in the session by the POST above, not by
    the URL alone. Someone who later comes across the link -- in a shared
    screenshot, a browser history, a log file -- gets sent to the lookup form,
    where the confirmation code alone is not enough either.
    """

    template_name = "web/reservation_confirmation.html"

    def get(self, request, code):
        if request.session.get(SESSION_RECENT_RESERVATION) != code:
            messages.info(
                request,
                "Para ver tu reserva necesitamos el codigo de confirmacion y el "
                "correo electronico con el que reservaste.",
            )
            return redirect("web:reservation-lookup")

        reservation = ReservationService().lookup_by_code(code)
        return render(request, self.template_name, {"reservation": reservation})


class ReservationLookupView(View):
    """Lets a guest without an account retrieve their booking."""

    template_name = "web/reservation_lookup.html"

    def get(self, request):
        return render(request, self.template_name, {})

    def post(self, request):
        code = request.POST.get("confirmation_code", "")
        email = request.POST.get("email", "")

        try:
            reservation = ReservationService().lookup(code, email)
        except ReservationDomainError as exc:
            messages.error(request, str(exc))
            return render(
                request, self.template_name, {"confirmation_code": code}
            )

        return render(
            request,
            "web/reservation_confirmation.html",
            {"reservation": reservation, "from_lookup": True},
        )
