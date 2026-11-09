      
      
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

        if (name === "map") initMap();

        if (name === "list") displayLockersList();
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
        settings.hidden = false;
      });

      document
        .getElementById("settings-close")
        .addEventListener("click", () => {
          settings.hidden = true;
        });

    



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