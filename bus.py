#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import sys
from datetime import datetime
from typing import Any, List, Dict, Optional

# --- CONFIGURATION ---
# Stop IDs: Comma separated string. 
# Get these from the URL at https://ucf.transloc.com/routes (click a stop)
STOP_IDS = "" 

# Filter (Optional): Add Route IDs here (integers) if you only want to see specific shuttles.
# Leave empty to show all routes at these stops.
# Example: INTERESTED_ROUTES = [4, 13]
INTERESTED_ROUTES: List[int] = []

API_HOST = "https://ucf.transloc.com"
API_PATH = "/Services/JSONPRelay.svc/GetStopArrivalTimes"
API_KEY = "" # Optional
VERSION = "2"
TIMEOUT_SECS = 10

def fetch_stop_arrival_times() -> Any:
    """Fetches data using standard urllib to avoid pip dependencies."""
    params = {
        "apiKey": API_KEY, 
        "stopIds": STOP_IDS, 
        "version": VERSION
    }
    # Encode params and build URL
    query_string = urllib.parse.urlencode(params)
    url = f"{API_HOST}{API_PATH}?{query_string}"
    
    # Create request with headers
    req = urllib.request.Request(
        url, 
        headers={
            "Accept": "application/json",
            "User-Agent": "HomeAssistant/BusTracker"
        }
    )
    
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as response:
        # json.load reads directly from the http response object
        return json.load(response)

def parse_arrivals(api_payload: Any) -> List[Dict[str, Any]]:
    """Parses the TransLoc JSON structure into a flat list of arrivals."""
    if not isinstance(api_payload, list):
        return []

    arrivals: List[Dict[str, Any]] = []

    for route_block in api_payload:
        if not isinstance(route_block, dict):
            continue

        route_id = route_block.get("RouteId")
        
        # Filter by route if configured
        if INTERESTED_ROUTES and (int(route_id) if route_id else 0) not in INTERESTED_ROUTES:
            continue

        route_desc = route_block.get("RouteDescription")
        stop_desc = route_block.get("StopDescription")
        stop_id = route_block.get("StopId")

        times = route_block.get("Times") or []
        if not isinstance(times, list) or not times:
            continue

        for t in times:
            if not isinstance(t, dict):
                continue

            try:
                seconds = int(t.get("Seconds"))
            except (ValueError, TypeError):
                continue

            is_arriving = bool(t.get("IsArriving", False))
            text = (t.get("Text") or "").strip().lower()

            arrivals.append({
                "route": route_desc,
                "route_id": route_id,
                "vehicle_id": t.get("VehicleId"),
                # Ceiling division to round up to the nearest minute
                "minutes": (seconds + 59) // 60,
                "status": "Arriving" if is_arriving or text == "arriving" else "En route",
                "stop": stop_desc,
                "stop_id": stop_id,
            })

    arrivals.sort(key=lambda x: x["minutes"])
    return arrivals

def build_homeassistant_json(api_payload: Any) -> Dict[str, Any]:
    """Structures the data for optimal consumption by HA sensors."""
    arrivals = parse_arrivals(api_payload)

    by_stop: Dict[Any, Dict[str, Any]] = {}
    
    # Group by Stop ID
    for a in arrivals:
        sid = a["stop_id"]
        s = by_stop.setdefault(sid, {"stop_id": sid, "stop": a["stop"], "etas": []})
        s["etas"].append({
            "route": a["route"],
            "route_id": a["route_id"],
            "vehicle_id": a["vehicle_id"],
            "minutes": a["minutes"],
            "status": a["status"],
        })

    # Sort ETAs within each stop and finalize stop list
    stops_list: List[Dict[str, Any]] = []
    for s in by_stop.values():
        s["etas"].sort(key=lambda e: e["minutes"])
        s["next_minutes"] = s["etas"][0]["minutes"] if s["etas"] else None
        s["routes_present"] = sorted({e["route"] for e in s["etas"] if e.get("route")})
        stops_list.append(s)

    # Sort stops so the one with the soonest bus is first (or primary)
    stops_list.sort(key=lambda s: (
        s["next_minutes"] is None, 
        s["next_minutes"] or 9999, 
        str(s["stop_id"])
    ))

    top_stop = stops_list[0] if stops_list and stops_list[0]["next_minutes"] is not None else None

    return {
        "next_minutes": top_stop["next_minutes"] if top_stop else None,
        "stop": top_stop["stop"] if top_stop else "No Active Routes",
        "stop_id": top_stop["stop_id"] if top_stop else None,
        "stops": stops_list,
        "count": len(arrivals)
    }

def main() -> None:
    try:
        raw_data = fetch_stop_arrival_times()
        out = build_homeassistant_json(raw_data)
        # Use separators to minify JSON slightly
        print(json.dumps(out, separators=(",", ":")))
    except Exception as e:
        # Return a valid JSON structure with the error so HA doesn't just log "JSON decode error"
        print(json.dumps({
            "next_minutes": None,
            "stop": "Error",
            "stop_id": None,
            "stops": [],
            "error": str(e),
        }, separators=(",", ":")))

if __name__ == "__main__":
    main()
