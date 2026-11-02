import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

/** Numbered pins on an OpenStreetMap map + cards with verified Google Maps data. */
export function PlacesPanel({ places }) {
  const el = useRef(null);
  const mapRef = useRef(null);

  useEffect(() => {
    if (!el.current || !places.length) return;
    const map = L.map(el.current, { scrollWheelZoom: false });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 18,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(map);
    const pts = places.map((p, i) => {
      const icon = L.divIcon({ className: "pin", html: `<span>${i + 1}</span>`, iconSize: [26, 26], iconAnchor: [13, 13] });
      L.marker([p.lat, p.lng], { icon })
        .addTo(map)
        .bindPopup(`<b>${i + 1}. ${p.name}</b><br>${p.address || ""}${p.maps_url ? `<br><a href="${p.maps_url}" target="_blank" rel="noreferrer">Open in Google Maps ↗</a>` : ""}`);
      return [p.lat, p.lng];
    });
    if (pts.length === 1) map.setView(pts[0], 13);
    else map.fitBounds(pts, { padding: [28, 28], maxZoom: 13 });
    mapRef.current = map;
    return () => map.remove();
  }, [places]);

  if (!places.length) return null;

  return (
    <div className="places">
      <h3>📍 On the map</h3>
      <div className="map" ref={el} />
      <div className="place-list">
        {places.map((p, i) => (
          <div
            key={p.id}
            className="place"
            onClick={() => mapRef.current?.setView([p.lat, p.lng], 14)}
            title="Show on map"
          >
            <span className="place-num">{i + 1}</span>
            <div className="place-text">
              <div className="place-name">{p.name}</div>
              <div className="place-meta">
                {p.rating != null && <span>★ {p.rating.toFixed(1)}{p.reviews ? ` (${p.reviews.toLocaleString()})` : ""}</span>}
                {p.price && <span>{p.price}</span>}
                {p.type && <span>{p.type}</span>}
                {p.open_now != null && <span className={p.open_now ? "open" : "closed"}>{p.open_now ? "Open now" : "Closed now"}</span>}
              </div>
              <div className="place-addr">{p.address}</div>
              <div className="place-links">
                {p.maps_url && <a href={p.maps_url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Google Maps ↗</a>}
                {p.website && <a href={p.website} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>Website ↗</a>}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
