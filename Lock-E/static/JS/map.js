// <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>

// ///////////////////////////////////////////////////////////////////////////
// //////////////////////////  Map related section  //////////////////////////
// ///////////////////////////////////////////////////////////////////////////
const LOCATION_KEY = "user-location-lock-e";

const locateBtn = document.getElementById("locate-btn");
const locateBadge = document.getElementById("locate-badge");
const locateHint = document.getElementById("locate-hint");

// Add a location point manually
let userMarker = null;
let placing = false;
let map = null;

function loadLocation() {
  try {
    return JSON.parse(localStorage.getItem(LOCATION_KEY));
  } catch {
    return null;
  }
}

function saveLocation(loc) {
  try {
    localStorage.setItem(LOCATION_KEY, JSON.stringify(loc));
  } catch {}
}

function drawUserMarker(loc) {
  if (userMarker) {
    userMarker.setLatLng([loc.lat, loc.lng]);
  } else {
    userMarker = L.circleMarker([loc.lat, loc.lng], {
      radius: 9,
      color: "#f3ebe2",
      fillColor: "#168AD9",
      fillOpacity: 0.9,
    }).addTo(map);
  }
}

function updateBadge() {
  locateBadge.hidden = !!loadLocation();
}

function setPlacing(on) {
  placing = on;
  if (on) setAdding(false);
  locateBtn.classList.toggle("placing", on);
  locateHint.hidden = !on;
  document.getElementById("map").classList.toggle("placing", on);
}

function initMap() {
  if (map) {
    map.invalidateSize();
    return;
  }

  startTrackingUserLocation();

  map = L.map("map").setView([35.855353, 128.485279], 15);
  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap",
  }).addTo(map);

  const saved = loadLocation();
  if (saved) {
    map.setView([saved.lat, saved.lng], 15);
    drawUserMarker(saved);
  }

  map.on("click", (e) => {
    const point = { lat: e.latlng.lat, lng: e.latlng.lng };

    if (placing) {
      saveLocation(point);
      drawUserMarker(point);
      setPlacing(false);
      updateBadge();
    } else if (adding) {
      openLockerForm(point);
    }
  });
}

locateBtn.addEventListener("click", () => {
  setPlacing(!placing);
  applyMethod("manual");
  showMethodTheme("manual");
  saveMethod("manual");
});
