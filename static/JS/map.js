// <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>

let map = null;
const locateBtn = document.getElementById("locate-btn");
const locationHint = document.getElementById("location-hint");

let userMarker = null;
let placing = false;

function initMap() {
  if (map) {
    map.invalidateSize();
    return;
  }

  map = L.map("map").setView([35.855353, 128.485279], 15);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  lockersLayer.addTo(map);
  displayLockersOnMap();

  // Set the location on the map by clicking on it
  locateBtn.addEventListener("click", () => {
    locateBtn.classList.toggle("placing");
    locationHint.hidden = !locateBtn.classList.contains("placing");
  });

  map.on("click", (e) => {
    if (!locateBtn.classList.contains("placing")) return;

    localStorage.setItem(
      "user_location",
      JSON.stringify({
        lat: e.latlng.lat,
        lng: e.latlng.lng,
      }),
    );

    displayUserLocation();

    locationHint.hidden = true;
    locateBtn.classList.remove("placing");
  });
}



const userIcon = L.divIcon({
  className: "user-marker",
  html: `
    <div class="user-dot">
      <span class="user-ring"></span>
      <span class="user-ring delay"></span>
      <span class="user-core"></span>
    </div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});

function displayUserLocation() {
  if (!map) return;

  let loc = null;
  try {
    loc = JSON.parse(localStorage.getItem("user_location"));
  } catch {}

  if (!loc) {
    if (userMarker) {
      userMarker.remove();
      userMarker = null;
    }
    return;
  }

  if (userMarker) {
    userMarker.setLatLng([loc.lat, loc.lng]);
  } else {
    userMarker = L.marker([loc.lat, loc.lng], {
      icon: userIcon,
      zIndexOffset: 1000,
      interactive: false,
      keyboard: false,
    }).addTo(map);
  }
}






// Display lockers on the map
const PROVIDER_EMOJI = {
  mondial_relay: "𝓜",
  vinted_go: "𝓥",
  pickup: "𝓟",
};

const lockersLayer = L.layerGroup(); // permet de tout effacer avant de redessiner

function lockerIcon(l) {
  const sizes = [
    ["S", l.small_compartments_left],
    ["M", l.medium_compartments_left],
    ["B", l.big_compartments_left]
  ];

  const total = sizes.reduce((sum, [, n]) => sum + n, 0);
  const ring = total > 0 ? "#22c55e" : "#ef4444";

  const rows = sizes
    .map(
      ([label, n]) =>
        `<div class="lk-row ${n > 0 ? "ok" : "none"}">${label}${n}</div>`
    )
    .join("");

  return L.divIcon({
    className: "locker-marker",
    html: `
      <div class="lk-wrap" style="--ring:${ring}">
        <div class="lk">
          <div class="lk-badge">${PROVIDER_EMOJI[l.locker_brand] ?? "🔒"}</div>
          <div class="lk-counts">${rows}</div>
        </div>
        <div class="lk-tail"></div>
        ${total > 0 ? '<div class="lk-pulse"></div>' : ""}
      </div>`,
    iconSize: [76, 54],
    iconAnchor: [38, 51] // la pointe est sur la position du locker
  });
}





async function displayLockersOnMap() {
  // Position de l'utilisateur, sinon centre de la carte
  const saved = JSON.parse(localStorage.getItem("user_location"));
  const pos = saved ?? { lat: map.getCenter().lat, lng: map.getCenter().lng };

  let lockers;
  try {
    const res = await fetch(
      `/api/get-lockers-info?lat=${pos.lat}&lon=${pos.lng}`,
    );
    if (!res.ok) throw new Error(res.status);
    lockers = await res.json();
  } catch (err) {
    console.error("Could not load lockers", err);
    return;
  }

  lockersLayer.clearLayers();

  for (const l of lockers) {
    const marker = L.marker([l.locker_latitude, l.locker_longitude], {
      icon: lockerIcon(l),
    });

    // Popup construit en DOM : textContent évite d'interpréter du HTML
    marker.on("click", () => {
      window.location.href = `/locker/${l.locker_id}`;
    });
    marker.addTo(lockersLayer);
  }
}
