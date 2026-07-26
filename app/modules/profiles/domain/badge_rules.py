"""
Pure domain logic for computing badges from trip statistics.
No framework imports — pure Python only.
"""

from app.modules.profiles.domain.entities import Badge


def compute_badges(
    trips_completed: int,
    trips_created: int,
    countries_visited_count: int,
    flight_count: int,
    bus_count: int,
    shared_trip_count: int,
) -> list[Badge]:
    """Derive which badges a user has earned based on raw counts."""
    badges: list[Badge] = []

    if trips_completed >= 1:
        badges.append(Badge.FIRST_TRIP)

    if countries_visited_count >= 20:
        badges.append(Badge.COUNTRIES_20)
    elif countries_visited_count >= 10:
        badges.append(Badge.COUNTRIES_10)
    elif countries_visited_count >= 5:
        badges.append(Badge.COUNTRIES_5)

    if flight_count >= 10:
        badges.append(Badge.FREQUENT_FLYER)

    if bus_count >= 5:
        badges.append(Badge.BUS_EXPLORER)

    if trips_created >= 10:
        badges.append(Badge.PLANNER_PRO)

    if shared_trip_count >= 5:
        badges.append(Badge.COLLABORATOR)

    return badges

