// ///////////////////////////////////////////////////////////////////////////
// ////////////////////// Navigating on the page /////////////////////////////
// ///////////////////////////////////////////////////////////////////////////

function showView(name) {
  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));
  document.getElementById("view-" + name).classList.add("active");

  document
    .querySelectorAll("nav button")
    .forEach((b) =>
      b.classList.toggle("active", b.dataset.view === name),
    );

  if (name === "map") {initMap(); displayLockersOnMap();};

  if (name === "list") displayLockersList();

  if (name === "booking") {displayBookingInfo(); displayUserInfo();}
  else clearInterval(bookingTimer);
}

document
  .querySelectorAll("nav button")
  .forEach((b) =>
    b.addEventListener("click", () => showView(b.dataset.view)),
  );



// ///////////////////////////////////////////////////////////////////////////
// ////////////////////// Displaying the settings ////////////////////////////
// ///////////////////////////////////////////////////////////////////////////

const settings = document.getElementById("settings");

document.getElementById("profile-btn").addEventListener("click", () => {
  displayUserInfo();
  settings.hidden = false;
});

document
  .getElementById("settings-close")
  .addEventListener("click", () => {
    settings.hidden = true;
  });



// ///////////////////////////////////////////////////////////////////////////
// ////////////////////// Displaying locker list  ////////////////////////////
// ///////////////////////////////////////////////////////////////////////////
  
async function displayLockersList() {
  const list = document.getElementById("locker-list");

  // Getting user's position saved in the browser
  const loc = JSON.parse(localStorage.getItem("user_location"));
  if (!loc) {
    list.innerHTML = "<h5 id='locationnotset'>Set your location on the map to see the nearest lockers</h5>";
    list.addEventListener("click", () => {
      showView("map");
      document.getElementById("location-hint").hidden = false;
      locateBtn.classList.toggle("placing", true);
    });
    return;
  }

  // Getting the list of every locker sorted by distances
  let lockers;
  try {
    const res = await fetch(
      `/api/get-lockers-info?lat=${loc.lat}&lon=${loc.lng}`,
    );
    if (!res.ok) throw new Error(res.status);
    lockers = await res.json();
  } catch (err) {
    list.innerHTML = "<li>Could not load lockers.</li>";
    return;
  }

  // Create a card for each locker in the list and add it in the list
  list.innerHTML = "";

  for (const l of lockers) {
    const li = document.createElement("li");
    li.className = "locker-item";

    li.addEventListener("click", () => {
      window.location.href = `/locker/${l.locker_id}`;
    });

    const info = document.createElement("div");

    const name = document.createElement("strong");
    name.textContent = l.locker_location_name;

    const dist = document.createElement("div");
    dist.className = "locker-distance";
    dist.textContent = `${l.distance_to_user_km} km`;

    const provider = document.createElement("div");
    provider.className = "locker-provider";
    provider.textContent = l.locker_brand.replace("_", " ");

    info.append(name, dist, provider);

    const bars = document.createElement("div");
    bars.className = "locker-bars";

    const sizes = [
      ["S", l.small_compartments_left],
      ["M", l.medium_compartments_left],
      ["B", l.big_compartments_left],
    ];

    for (const [label, count] of sizes) {
      const col = document.createElement("div");
      col.className = "bar-col";
      col.title = `${count} free (${label})`;

      const bar = document.createElement("div");
      bar.className = "bar" + (count === 0 ? " empty" : "");
      bar.style.height = 4 + Math.min(count, 4) * 4 + "px";

      const text = document.createElement("span");
      text.className = "bar-label " + (count > 0 ? "ok" : "none");
      text.textContent = `${label}${count}`;

      col.append(bar, text);
      bars.append(col);
    }

    li.append(info, bars);
    list.append(li);
  }
}



// ///////////////////////////////////////////////////////////////////////////
// ////////////////////// Displaying booking info  ///////////////////////////
// ///////////////////////////////////////////////////////////////////////////

let bookingTimer = null;

async function displayBookingInfo() {
  const box = document.getElementById("booking-content");
  clearInterval(bookingTimer);

  let data;
  try {
    const res = await fetch("/api/get-reservation-info");
    if (!res.ok) throw new Error(res.status);
    data = await res.json();
  } catch {
    box.innerHTML = "<p>Could not load your booking</p>";
    return;
  }

  if (!data.reservation_id) {
    box.innerHTML = "<p>You have no active booking</p>";
    return;
  }

  const sizes = { 1: "Small", 2: "Medium", 3: "Big" };

  const card = document.createElement("div");
  card.className = "booking-card";

  const title = document.createElement("strong");
  title.textContent = data.locker_name;

  const sub = document.createElement("div");
  sub.className = "booking-sub";
  sub.textContent = `${sizes[data.size]} · compartment #${data.compartment_number}`;

  const codeLabel = document.createElement("div");
  codeLabel.className = "booking-sub";
  codeLabel.textContent = "Your code";

  const code = document.createElement("div");
  code.className = "booking-code";
  code.textContent = data.code;

  const timer = document.createElement("div");
  timer.className = "booking-timer";

  const simu_button = document.createElement("button");
  simu_button.onclick = simulateDeposit;
  simu_button.className = "deposit-simulation-button";
  simu_button.textContent = "Simulate deposit";

  card.append(title, sub, codeLabel, code, timer, simu_button);
  box.replaceChildren(card);

  const end = Date.now() + data.seconds_left * 1000;

  async function tick() {
    const left = Math.max(0, Math.round((end - Date.now()) / 1000 + 1 ));
    const m = String(Math.floor(left / 60)).padStart(2, "0");
    const s = String(left % 60).padStart(2, "0");
    timer.textContent = `${m}:${s}`;

    if (left === 0) {
      clearInterval(bookingTimer);
      box.innerHTML = "<p>Your booking has expired</p>";
      await fetch("/cancel-reservations").catch(console.error);
      displayUserInfo();
    }
  }

  tick();
  bookingTimer = setInterval(tick, 1000);
}



// ///////////////////////////////////////////////////////////////////////////
// ///////////////////////// Displaying user info ////////////////////////////
// ///////////////////////////////////////////////////////////////////////////

// In this part we want to display user info as name and email in the parameter 
// section. But also penalty score, streak, and the date the user can reserve 
// compartments again if he has an active penalty in the booking view.

async function displayUserInfo() {
  try {
    const res = await fetch("/api/get-user-information");
    if (!res.ok) throw new Error(res.status);
    const user = await res.json();

    document.getElementById("user-name-set").textContent = `Name : ${user.name}`;
    document.getElementById("user-email-set").textContent = `Email : ${user.email}`;

    const box = document.getElementById("user-penalty-info");
    box.replaceChildren();

    const addLine = (text, className = "") => {
      const p = document.createElement("p");
      p.textContent = text;
      if (className) p.className = className;
      box.append(p);
    };

    addLine(`Penalty score : ${user.penalty_score}`);

    // Exactement 1 point : simple avertissement
    if (user.penalty_score === 1) {
      addLine(
        "Warning: your next missed reservation will lock your account for 24h.",
        "penalty-warning",
      );
    }

    // Plus de 1 point : streak et temps restant
    if (user.penalty_score > 1) {
      addLine(`Streak : ${user.streak}/7 successful reservation in a row`);

      if (user.locked_deadline) {
        const deadline = new Date(user.locked_deadline);
        const msLeft = deadline - Date.now();

      if (msLeft > 0) {
        const totalMin = Math.ceil(msLeft / 60000);
        const dd = String(Math.floor(totalMin / 1440)).padStart(2, "0");
        const hh = String(Math.floor((totalMin % 1440) / 60)).padStart(2, "0");
        const mm = String(totalMin % 60).padStart(2, "0");
        addLine(`Time left on your penalty : ${dd}d ${hh}h ${mm}m`, "penalty-locked");
      }
      }
    }
  } catch (err) {
    console.error(err);
  }
}



// ///////////////////////////////////////////////////////////////////////////
// /////////////////////////// Simulate deposit //////////////////////////////
// ///////////////////////////////////////////////////////////////////////////

async function simulateDeposit() {
  try {
    const res = await fetch("/simulate-deposit");
    const data = await res.json();
    if (res.ok) {
      alert(data.message);
      displayBookingInfo()
    } else {
      alert(data.error);
    }
  } catch {
    alert("Connection with the database imposible");
  }
  displayUserInfo();
}



// ///////////////////////////////////////////////////////////////////////////
// ////////////////////////// Map initialization /////////////////////////////
// ///////////////////////////////////////////////////////////////////////////

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


// ///////////////////////////////////////////////////////////////////////////
// ////////////////// Display User location on the Map ///////////////////////
// ///////////////////////////////////////////////////////////////////////////

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



// ///////////////////////////////////////////////////////////////////////////
// /////////////// Display icons on the map for each locker //////////////////
// ///////////////////////////////////////////////////////////////////////////

const PROVIDER_EMOJI = {
  mondial_relay: "𝓜",
  vinted_go: "𝓥",
  pickup: "𝓟",
};

const lockersLayer = L.layerGroup();

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
    iconAnchor: [38, 51]
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