# User Manual

## Roles
* **User** — scans, fields, plants, environment records, simulations, pollination logs, reports (own data only).
* **Researcher** — everything a user can do + add species reference images, see all-account analytics, model registry.
* **Administrator** — + user management (roles, deactivate), activity log, reload models.

## Scanning flowers
1. **Flower scanner → Upload**: drop or choose a JPEG/PNG/WEBP/BMP (≤ 15 MB). On phones this can open the camera.
2. **Mode**
   * *auto* — runs the orchard-trained detector; if nothing confident is found, analyses the image as a single close-up and says so.
   * *scene* — many flowers (orchard rows, trees).
   * *close-up* — one flower filling the frame (recommended for hibiscus, tomato, chilli, brinjal, sunflower, strawberry).
3. **Species** — leave on "let the model decide" or declare it. Declared species are labelled `user declared`.
4. Optional: attach an **environment record** (affects readiness confidence) and a **plant**.
5. Read the results: click a box or table row for its species, stage, centre, health, pose and readiness card.

### Camera & live scanning
* **Start camera** → allow the permission. **Switch** cycles cameras (front/back).
* **Start live scan** samples one frame every *N* seconds (slider). Boxes come from the backend; slower laptops should use longer
  intervals. Live frames are not stored.
* **Capture & analyse** stores a full analysis of the current frame.
* **Phones need HTTPS.** Options: deploy (Vercel/Render), run a tunnel (`cloudflared tunnel --url http://localhost:5173`), or
  enable HTTPS in Vite (`npm i -D @vitejs/plugin-basic-ssl` and add it to `vite.config.ts`). If permission was denied, re-enable
  it in the browser's site settings.

## Understanding the labels
| Badge | Meaning |
|---|---|
| trained model | measured detector (see Model evaluation) |
| reference gallery | nearest-neighbour species match; `unknown` below threshold |
| heuristic | rule-of-thumb image analysis; not trained on labels |
| rule engine | readiness rules from the species knowledge base |
| simulation | computational only |
| close-up fallback | whole image treated as one flower — not a detection |
| user declared | you selected it |

**Readiness categories:** likely ready · approaching · past window · not ready · indeterminate (species unknown).
They are *visual estimates*; pollen viability and stigma receptivity are not observable in photos.

## Simulator
Pick a species profile, adjust alignment offset, wind, humidity, vibration frequency (vibration crops), particles and seed,
then **Run simulation**. Use the timeline to scrub, orbit the 3-D view with the mouse/touch, or switch to 2-D. **Sweeps** show
how simulated transfer efficiency changes with one parameter. The four result tiles keep detection accuracy, simulation
completion, simulated efficiency and biological outcome (always "not measured") separate.

## Records & reports
* **Fields / Inventory** — locations and individual plants.
* **Environment** — manual observations or *Fetch* from Open-Meteo (uses your location or a field's coordinates); each record
  shows its source and retrieval time. Use *Assess* to see species-specific environmental factors.
* **Pollination history** — log real actions (method, flowers, time) and later update the observed outcome.
* **Reports** — PDF summary, CSV of every analysed flower, JSON per scan.

## Adding a new crop (researchers)
Add the species to the knowledge base JSON, then upload 20+ diverse reference photos from *Species recognition → Add reference*.
Keep some photos aside as a test set before trusting the results.
