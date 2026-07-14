import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";
import type { Museum } from "../types";

// Correctif classique : Vite ne résout pas les icônes par défaut de Leaflet
const defaultIcon = L.icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
});

const PARIS_CENTER: [number, number] = [48.8566, 2.3522];

interface MapViewProps {
  museums: Museum[];
  onSelectMuseum?: (museumId: number) => void;
}

export default function MapView({ museums, onSelectMuseum }: MapViewProps) {
  const located = museums.filter(
    (m): m is Museum & { latitude: number; longitude: number } =>
      m.latitude !== null && m.longitude !== null,
  );

  return (
    <div className="relative h-[600px] overflow-hidden rounded-xl border border-ink/10 dark:border-cream/10">
      {located.length === 0 && (
        <div className="absolute inset-0 z-[500] flex items-center justify-center bg-cream/70 dark:bg-ink/70 pointer-events-none">
          <p className="rounded-lg bg-white dark:bg-ink px-4 py-2 text-sm shadow">
            Aucun musée ne correspond à ces filtres.
          </p>
        </div>
      )}
      <MapContainer center={PARIS_CENTER} zoom={10} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {located.map((museum) => (
          <Marker key={museum.id} position={[museum.latitude, museum.longitude]} icon={defaultIcon}>
            <Popup>
              <strong>{museum.name}</strong>
              <br />
              {museum.city ?? ""}
              <br />
              {museum.upcoming_events_count > 0 ? (
                <button
                  type="button"
                  className="text-ocre-dark underline"
                  onClick={() => onSelectMuseum?.(museum.id)}
                >
                  {museum.upcoming_events_count} événement(s) à venir
                </button>
              ) : (
                <em>Pas d'événement à venir</em>
              )}
              {museum.website_url && (
                <>
                  <br />
                  <a href={museum.website_url} target="_blank" rel="noopener noreferrer">
                    Site officiel
                  </a>
                </>
              )}
              <br />
              <Link to={`/?museum=${museum.id}`}>Voir dans la liste</Link>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
