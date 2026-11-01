"""Dynamic vehicle routing optimizer utilizing Haversine matrices, Nearest Neighbor, and 2-Opt local search."""

from datetime import date, datetime, timezone
import math
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from src.models.entities import Alert, Business, CollectionRoute, Container
from src.models.enums import AlertType, ContainerStatus, RouteStatus

EARTH_RADIUS_KM = 6371.0

# Central logistics hub: Reoil Dominicana SPM Logistics Hub
DEPOT_SPEC = {
    "business_id": "DEPOT_REOIL_SPM",
    "business_name": "Reoil SPM Depot",
    "latitude": 18.4650,
    "longitude": -69.2950,
    "address": "Zona Industrial SPM, San Pedro de Macorís",
    "estimated_liters": 0.0,
    "is_depot": True,
}


def haversine_distance(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate the great circle distance between two geographic coordinates in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def calculate_tour_distance(tour: List[Dict[str, Any]]) -> float:
    """Calculate total travel distance along a sequential tour in kilometers."""
    if len(tour) < 2:
        return 0.0
    total = 0.0
    for idx in range(len(tour) - 1):
        total += haversine_distance(
            tour[idx]["latitude"],
            tour[idx]["longitude"],
            tour[idx + 1]["latitude"],
            tour[idx + 1]["longitude"],
        )
    return total


class RoutingService:
    """Logistics route synthesizer and heuristic vehicle routing optimizer."""

    @staticmethod
    def construct_nearest_neighbor_tour(
        stops: List[Dict[str, Any]],
        depot: Dict[str, Any] = DEPOT_SPEC,
    ) -> List[Dict[str, Any]]:
        """Greedily construct an initial roundtrip tour starting and ending at the depot."""
        if not stops:
            return [dict(depot), dict(depot)]

        unvisited = [dict(s) for s in stops]
        tour = [dict(depot)]
        current = depot

        while unvisited:
            next_stop = min(
                unvisited,
                key=lambda s: haversine_distance(
                    current["latitude"],
                    current["longitude"],
                    s["latitude"],
                    s["longitude"],
                ),
            )
            tour.append(next_stop)
            unvisited.remove(next_stop)
            current = next_stop

        # Return to logistics depot
        tour.append(dict(depot))
        return tour

    @staticmethod
    def refine_tour_2opt(
        tour: List[Dict[str, Any]],
        min_improvement_km: float = 0.005,
    ) -> List[Dict[str, Any]]:
        """Refine an existing tour via 2-Opt edge swaps, untangling crossings while preserving fixed depot terminals."""
        n = len(tour)
        if n <= 3:
            return tour

        optimized_tour = list(tour)
        improved = True

        while improved:
            improved = False
            for i in range(0, n - 2):
                for j in range(i + 2, n - 1):
                    # Current edge distance sum: (i -> i+1) + (j -> j+1)
                    d_current = (
                        haversine_distance(
                            optimized_tour[i]["latitude"],
                            optimized_tour[i]["longitude"],
                            optimized_tour[i + 1]["latitude"],
                            optimized_tour[i + 1]["longitude"],
                        )
                        + haversine_distance(
                            optimized_tour[j]["latitude"],
                            optimized_tour[j]["longitude"],
                            optimized_tour[j + 1]["latitude"],
                            optimized_tour[j + 1]["longitude"],
                        )
                    )

                    # New edge distance sum if sub-tour is reversed: (i -> j) + (i+1 -> j+1)
                    d_new = (
                        haversine_distance(
                            optimized_tour[i]["latitude"],
                            optimized_tour[i]["longitude"],
                            optimized_tour[j]["latitude"],
                            optimized_tour[j]["longitude"],
                        )
                        + haversine_distance(
                            optimized_tour[i + 1]["latitude"],
                            optimized_tour[i + 1]["longitude"],
                            optimized_tour[j + 1]["latitude"],
                            optimized_tour[j + 1]["longitude"],
                        )
                    )

                    # Check for significant geometric improvement
                    if (d_current - d_new) >= min_improvement_km:
                        optimized_tour[i + 1 : j + 1] = list(
                            reversed(optimized_tour[i + 1 : j + 1])
                        )
                        improved = True
                        break
                if improved:
                    break

        return optimized_tour

    @classmethod
    def optimize_itinerary(
        cls,
        stops: List[Dict[str, Any]],
        depot: Dict[str, Any] = DEPOT_SPEC,
    ) -> Dict[str, Any]:
        """Execute Nearest-Neighbor construction followed by 2-Opt local search refinement."""
        raw_tour = cls.construct_nearest_neighbor_tour(stops, depot=depot)
        optimized_tour = cls.refine_tour_2opt(raw_tour)

        # Assign final sequence numbers and cumulative distances
        final_itinerary = []
        cumulative_distance = 0.0
        cumulative_liters = 0.0

        for seq, stop in enumerate(optimized_tour, start=1):
            if seq > 1:
                prev_stop = final_itinerary[-1]
                leg_dist = haversine_distance(
                    prev_stop["latitude"],
                    prev_stop["longitude"],
                    stop["latitude"],
                    stop["longitude"],
                )
                cumulative_distance += leg_dist

            liters = float(stop.get("estimated_liters", 0.0))
            cumulative_liters += liters

            stop_entry = {
                "sequence": seq,
                "business_id": stop.get("business_id", "DEPOT"),
                "business_name": stop.get("business_name", "Depot"),
                "latitude": stop["latitude"],
                "longitude": stop["longitude"],
                "address": stop.get("address", ""),
                "estimated_liters": round(liters, 2),
                "fill_percentage": round(float(stop.get("fill_percentage", 80.0)), 1),
                "cumulative_distance_km": round(cumulative_distance, 2),
                "is_depot": stop.get("is_depot", False),
                "visited": stop.get("visited", False),
                "visited_at": stop.get("visited_at", None),
            }
            final_itinerary.append(stop_entry)

        return {
            "itinerary": final_itinerary,
            "total_distance_km": round(cumulative_distance, 2),
            "total_estimated_liters": round(
                sum(s.get("estimated_liters", 0.0) for s in stops), 2
            ),
            "total_stops": len(stops),
        }

    @classmethod
    def generate_daily_route(
        cls,
        db: Session,
        collector_user_id: Optional[str] = None,
        target_date: Optional[date] = None,
    ) -> CollectionRoute:
        """Collect all establishments with active 80% alerts and synthesize an optimized route."""
        sched_date = target_date or date.today()

        # 1. Query businesses having unresolved capacity alerts
        query = (
            db.query(Business, Container, Alert)
            .join(Container, Business.id == Container.business_id)
            .join(Alert, Container.id == Alert.container_id)
            .filter(
                Alert.is_resolved == False,
                Alert.alert_type.in_(
                    [AlertType.CAPACITY_80_PERCENT, AlertType.CAPACITY_95_CRITICAL]
                ),
            )
            .all()
        )

        # Consolidate by business so each physical location is visited once
        stops_by_biz: Dict[str, Dict[str, Any]] = {}
        for business, container, _ in query:
            if business.id not in stops_by_biz:
                stops_by_biz[business.id] = {
                    "business_id": str(business.id),
                    "business_name": business.name,
                    "latitude": business.latitude,
                    "longitude": business.longitude,
                    "address": business.address,
                    "estimated_liters": container.current_volume_liters,
                    "fill_percentage": round(container.current_fill_percentage or 80.0, 1),
                    "is_depot": False,
                }
            else:
                stops_by_biz[business.id]["estimated_liters"] += container.current_volume_liters

        # Fallback to high-fill containers if no alert records exist yet
        if not stops_by_biz:
            high_fill_containers = (
                db.query(Business, Container)
                .join(Container, Business.id == Container.business_id)
                .filter(
                    Container.status == ContainerStatus.ACTIVE,
                    Container.current_fill_percentage >= 70.0,
                )
                .all()
            )
            for business, container in high_fill_containers:
                if business.id not in stops_by_biz:
                    stops_by_biz[business.id] = {
                        "business_id": str(business.id),
                        "business_name": business.name,
                        "latitude": business.latitude,
                        "longitude": business.longitude,
                        "address": business.address,
                        "estimated_liters": container.current_volume_liters,
                        "fill_percentage": round(container.current_fill_percentage or 80.0, 1),
                        "is_depot": False,
                    }

        stops_list = list(stops_by_biz.values())
        optimization_result = cls.optimize_itinerary(stops_list)

        new_route = CollectionRoute(
            scheduled_date=sched_date,
            status=RouteStatus.SUGGESTED,
            total_distance_km=optimization_result["total_distance_km"],
            total_estimated_volume_liters=optimization_result["total_estimated_liters"],
            stops_order_json=optimization_result["itinerary"],
            collector_user_id=collector_user_id,
        )
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        return new_route

    @classmethod
    def confirm_stop(
        cls,
        route_id: str,
        business_id: str,
        db: Session,
    ) -> Dict[str, Any]:
        """Acknowledge collector pickup at an establishment stop, resetting container volume and resolving alerts."""
        route = db.query(CollectionRoute).filter(CollectionRoute.id == route_id).first()
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Route '{route_id}' not found",
            )

        stops = list(route.stops_order_json)
        stop_found = False
        now_utc = datetime.now(timezone.utc)

        for stop in stops:
            if stop.get("business_id") == business_id and not stop.get("is_depot"):
                stop["visited"] = True
                stop["visited_at"] = now_utc.isoformat()
                stop_found = True

        if not stop_found:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Business '{business_id}' is not an active uncompleted stop on route '{route_id}'",
            )

        # 1. Reset container tare volume for this business
        containers = db.query(Container).filter(Container.business_id == business_id).all()
        for container in containers:
            container.current_volume_liters = 0.0
            container.current_fill_percentage = 0.0
            container.updated_at = now_utc

            # 2. Auto-resolve pending capacity alerts for this container
            alerts = (
                db.query(Alert)
                .filter(Alert.container_id == container.id, Alert.is_resolved == False)
                .all()
            )
            for alert in alerts:
                alert.is_resolved = True
                alert.resolved_at = now_utc

        # 3. Check if all business stops in route have been visited
        non_depot_stops = [s for s in stops if not s.get("is_depot")]
        all_visited = all(s.get("visited", False) for s in non_depot_stops)

        route.stops_order_json = stops
        flag_modified(route, "stops_order_json")
        if all_visited and non_depot_stops:
            route.status = RouteStatus.COMPLETED
            route.completed_at = now_utc
        else:
            route.status = RouteStatus.IN_PROGRESS

        route.updated_at = now_utc
        db.commit()

        return {
            "status": "stop_confirmed",
            "route_id": str(route.id),
            "business_id": business_id,
            "route_status": (
                route.status.value
                if hasattr(route.status, "value")
                else str(route.status)
            ),
            "confirmed_at": now_utc.isoformat(),
        }
