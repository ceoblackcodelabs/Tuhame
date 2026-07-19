# Tuhame/mixins.py
"""
Shared access-control mixins used across the admin/dashboard side of the
site (properties, clients, payments, contracts, reports).

The rule: a normal logged-in user (a landlord/property owner/staff member)
should only ever see data tied to properties *they* own. A superuser
(is_superuser=True) can see everything, across all landlords.
"""


class OwnerScopedQuerysetMixin:
    """
    Drop this in front of ListView/DetailView/UpdateView/DeleteView to
    automatically scope the queryset to the logged-in user, unless they're
    a superuser.

    Because DetailView/UpdateView/DeleteView all resolve get_object() via
    get_queryset() under the hood, this also prevents a landlord from
    viewing/editing/deleting another landlord's object just by guessing its
    URL/pk - trying to do so now raises a normal 404 instead.

    Set `owner_lookup` to the ORM path from this model to the owning User,
    e.g. 'owner' for Property, 'property__owner' for Booking/Contract/Bill,
    'invoice__property__owner' for a Payment, or 'generated_by' for Report.
    """
    owner_lookup = 'owner'

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_superuser:
            return queryset
        return queryset.filter(**{self.owner_lookup: user}).distinct()


def scope_to_owner(queryset, user, owner_lookup='owner'):
    """
    Functional equivalent of OwnerScopedQuerysetMixin for use inside plain
    function-based views or get_context_data() aggregate queries (e.g.
    dashboard stats) that aren't backed by a single ListView queryset.
    """
    if user.is_superuser:
        return queryset
    return queryset.filter(**{owner_lookup: user}).distinct()
