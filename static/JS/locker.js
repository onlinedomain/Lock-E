// ---------- Distance ----------
function haversineKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const rad = d => (d * Math.PI) / 180;
  const a =
    Math.sin(rad(lat2 - lat1) / 2) ** 2 +
    Math.cos(rad(lat1)) *
      Math.cos(rad(lat2)) *
      Math.sin(rad(lon2 - lon1) / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

const locker = document.getElementById("locker");

try {
  const loc = JSON.parse(localStorage.getItem("user_location"));
  if (loc) {
    const km = haversineKm(
      loc.lat,
      loc.lng,
      parseFloat(locker.dataset.lat),
      parseFloat(locker.dataset.lng)
    );
    document.getElementById("distance").textContent = `${km.toFixed(2)} km`;
  } else {
    document.getElementById("distance").textContent =
      "Set your location on the map to see the distance";
  }
} catch {}

// ---------- Size selection ----------
const reserveBtn = document.getElementById("reserve-btn");
let selectedSize = null;

document.querySelectorAll(".choice").forEach(btn => {
  btn.addEventListener("click", () => {
    const size = Number(btn.dataset.size);
    selectedSize = selectedSize === size ? null : size;

    document
      .querySelectorAll(".choice")
      .forEach(b =>
        b.classList.toggle("selected", Number(b.dataset.size) === selectedSize)
      );
    reserveBtn.disabled = selectedSize === null;
  });
});

// ---------- Reservation ----------
reserveBtn.addEventListener("click", async () => {
  reserveBtn.disabled = true;

  try {
    const res = await fetch(
      `/reserve-compartment?locker_id=${locker.dataset.id}&size=${selectedSize}`
    );
    const data = await res.json();

    if (res.ok) {
      alert(data.message);
      window.location.href = "/"; 
    } else {
      alert(data.error);
      reserveBtn.disabled = false;
    }
  } catch {
    alert(data.error);
    reserveBtn.disabled = false;
  }
});
