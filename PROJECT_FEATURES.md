# PROJECT_FEATURES.md - EuroWander Roadmap

## Phase 1: Core Foundation & Security
- [ ] **FastAPI Setup:** Production-ready boilerplate with MongoDB Atlas.
- [ ] **Auth:** Secure User Login/Signup (JWT or Firebase).
- [ ] **Trip Entity:** Basic CRUD for Trip metadata (Destination, Dates, UserID).

## Phase 2: Flight Intelligence
- [ ] **SerpApi Integration:** Parse Google Flights data into domain models.
- [ ] **Recommendation Algorithm:** Logic to rank flights by price/time.
- [ ] **IATA Service:** Lookup codes for airports.

## Phase 3: Accommodation & Transport
- [ ] **Hotel Search:** Booking.com API (RapidAPI) integration.
- [ ] **Intercity Transit:** Bus/Train search logic.
- [ ] **Selection logic:** Linking hotels/transport to specific Trips.

## Phase 4: Discovery & Daily Itinerary
- [ ] **POI Discovery:** Google Places API for city landmarks.
- [ ] **Itinerary Builder:** Organizers POIs into "Days" within a Trip.
- [ ] **Favorites:** Saving "Must-See" locations.

## Phase 5: Budgeting & Costing
- [ ] **Budget Tracker:** Track expenses per trip category.
- [ ] **Cost Aggregator:** Total estimated vs. actual spend.