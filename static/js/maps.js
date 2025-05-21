// Initialize maps and geofencing functionality
let map;
let markers = [];
let geofenceCircles = [];
let directionsService;
let directionsRenderer;

// Initialize the map
function initMap() {
    // Check if the map element exists on the page
    const mapElement = document.getElementById('map');
    if (!mapElement) return;

    // Create the map centered on the US
    map = new google.maps.Map(mapElement, {
        center: { lat: 39.8283, lng: -98.5795 },
        zoom: 4,
        styles: [
            { elementType: "geometry", stylers: [{ color: "#242f3e" }] },
            { elementType: "labels.text.stroke", stylers: [{ color: "#242f3e" }] },
            { elementType: "labels.text.fill", stylers: [{ color: "#746855" }] },
            {
                featureType: "administrative.locality",
                elementType: "labels.text.fill",
                stylers: [{ color: "#d59563" }],
            },
            {
                featureType: "poi",
                elementType: "labels.text.fill",
                stylers: [{ color: "#d59563" }],
            },
            {
                featureType: "poi.park",
                elementType: "geometry",
                stylers: [{ color: "#263c3f" }],
            },
            {
                featureType: "poi.park",
                elementType: "labels.text.fill",
                stylers: [{ color: "#6b9a76" }],
            },
            {
                featureType: "road",
                elementType: "geometry",
                stylers: [{ color: "#38414e" }],
            },
            {
                featureType: "road",
                elementType: "geometry.stroke",
                stylers: [{ color: "#212a37" }],
            },
            {
                featureType: "road",
                elementType: "labels.text.fill",
                stylers: [{ color: "#9ca5b3" }],
            },
            {
                featureType: "road.highway",
                elementType: "geometry",
                stylers: [{ color: "#746855" }],
            },
            {
                featureType: "road.highway",
                elementType: "geometry.stroke",
                stylers: [{ color: "#1f2835" }],
            },
            {
                featureType: "road.highway",
                elementType: "labels.text.fill",
                stylers: [{ color: "#f3d19c" }],
            },
            {
                featureType: "transit",
                elementType: "geometry",
                stylers: [{ color: "#2f3948" }],
            },
            {
                featureType: "transit.station",
                elementType: "labels.text.fill",
                stylers: [{ color: "#d59563" }],
            },
            {
                featureType: "water",
                elementType: "geometry",
                stylers: [{ color: "#17263c" }],
            },
            {
                featureType: "water",
                elementType: "labels.text.fill",
                stylers: [{ color: "#515c6d" }],
            },
            {
                featureType: "water",
                elementType: "labels.text.stroke",
                stylers: [{ color: "#17263c" }],
            },
        ],
    });

    // Initialize directions service
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
        map: map,
        suppressMarkers: true,
        polylineOptions: {
            strokeColor: '#4285F4',
            strokeOpacity: 0.8,
            strokeWeight: 5
        }
    });

    // Check if we're on a specific page to initialize appropriate functionality
    if (document.getElementById('load-detail-map')) {
        initLoadDetailMap();
    } else if (document.getElementById('geofencing-map')) {
        initGeofencingMap();
    } else if (document.getElementById('tracking-map')) {
        initTrackingMap();
    }
}

// Initialize map for load detail page
function initLoadDetailMap() {
    const loadId = document.getElementById('load-detail-map').dataset.loadId;
    
    if (!loadId) return;
    
    // Fetch load data
    fetch(`/loads/${loadId}/data`)
        .then(response => response.json())
        .then(data => {
            if (!data) return;
            
            // Add pickup and delivery markers
            const bounds = new google.maps.LatLngBounds();
            
            if (data.pickup && data.pickup.lat && data.pickup.lng) {
                const pickupMarker = new google.maps.Marker({
                    position: { lat: data.pickup.lat, lng: data.pickup.lng },
                    map: map,
                    title: `Pickup: ${data.pickup.name}`,
                    icon: {
                        url: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
                        scaledSize: new google.maps.Size(32, 32)
                    }
                });
                
                markers.push(pickupMarker);
                bounds.extend(pickupMarker.getPosition());
                
                // Add pickup geofence circle
                if (data.pickup.geofence_radius) {
                    const pickupCircle = new google.maps.Circle({
                        strokeColor: '#4CAF50',
                        strokeOpacity: 0.8,
                        strokeWeight: 2,
                        fillColor: '#4CAF50',
                        fillOpacity: 0.1,
                        map: map,
                        center: { lat: data.pickup.lat, lng: data.pickup.lng },
                        radius: data.pickup.geofence_radius * 1609.34 // Convert miles to meters
                    });
                    
                    geofenceCircles.push(pickupCircle);
                }
            }
            
            if (data.delivery && data.delivery.lat && data.delivery.lng) {
                const deliveryMarker = new google.maps.Marker({
                    position: { lat: data.delivery.lat, lng: data.delivery.lng },
                    map: map,
                    title: `Delivery: ${data.delivery.name}`,
                    icon: {
                        url: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
                        scaledSize: new google.maps.Size(32, 32)
                    }
                });
                
                markers.push(deliveryMarker);
                bounds.extend(deliveryMarker.getPosition());
                
                // Add delivery geofence circle
                if (data.delivery.geofence_radius) {
                    const deliveryCircle = new google.maps.Circle({
                        strokeColor: '#F44336',
                        strokeOpacity: 0.8,
                        strokeWeight: 2,
                        fillColor: '#F44336',
                        fillOpacity: 0.1,
                        map: map,
                        center: { lat: data.delivery.lat, lng: data.delivery.lng },
                        radius: data.delivery.geofence_radius * 1609.34 // Convert miles to meters
                    });
                    
                    geofenceCircles.push(deliveryCircle);
                }
            }
            
            // Add last known vehicle position if available
            if (data.last_locations && data.last_locations.length > 0) {
                const lastLocation = data.last_locations[0];
                const vehicleMarker = new google.maps.Marker({
                    position: { lat: lastLocation.lat, lng: lastLocation.lng },
                    map: map,
                    title: 'Current Vehicle Position',
                    icon: {
                        url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                        scaledSize: new google.maps.Size(32, 32)
                    }
                });
                
                markers.push(vehicleMarker);
                bounds.extend(vehicleMarker.getPosition());
                
                // Calculate and display route
                if (data.status === 'in_transit' && data.delivery && data.delivery.lat && data.delivery.lng) {
                    calculateAndDisplayRoute(
                        { lat: lastLocation.lat, lng: lastLocation.lng },
                        { lat: data.delivery.lat, lng: data.delivery.lng }
                    );
                }
            }
            
            // Fit map to bounds with padding
            map.fitBounds(bounds, { padding: 50 });
            
            // If we only have one point, zoom out a bit
            if (markers.length === 1) {
                map.setZoom(10);
            }
        })
        .catch(error => console.error('Error fetching load data:', error));
}

// Initialize map for geofencing page
function initGeofencingMap() {
    // Load all facilities with geofences
    fetch('/geofencing/facilities')
        .then(response => response.json())
        .then(facilities => {
            if (!facilities || facilities.length === 0) return;
            
            const bounds = new google.maps.LatLngBounds();
            
            facilities.forEach(facility => {
                if (!facility.lat || !facility.lng) return;
                
                // Add facility marker
                const marker = new google.maps.Marker({
                    position: { lat: facility.lat, lng: facility.lng },
                    map: map,
                    title: facility.name,
                    icon: {
                        url: 'http://maps.google.com/mapfiles/ms/icons/purple-dot.png',
                        scaledSize: new google.maps.Size(32, 32)
                    }
                });
                
                markers.push(marker);
                bounds.extend(marker.getPosition());
                
                // Add geofence circle
                if (facility.geofence_radius) {
                    const circle = new google.maps.Circle({
                        strokeColor: '#9C27B0',
                        strokeOpacity: 0.8,
                        strokeWeight: 2,
                        fillColor: '#9C27B0',
                        fillOpacity: 0.1,
                        map: map,
                        center: { lat: facility.lat, lng: facility.lng },
                        radius: facility.geofence_radius * 1609.34, // Convert miles to meters
                        editable: true
                    });
                    
                    geofenceCircles.push(circle);
                    
                    // Add click event to select facility
                    google.maps.event.addListener(circle, 'click', function() {
                        selectFacility(facility.id);
                    });
                    
                    google.maps.event.addListener(marker, 'click', function() {
                        selectFacility(facility.id);
                    });
                    
                    // Listen for radius changes
                    google.maps.event.addListener(circle, 'radius_changed', function() {
                        updateFacilityGeofence(facility.id, marker.getPosition(), circle.getRadius());
                    });
                }
            });
            
            // Fit map to bounds
            map.fitBounds(bounds);
        })
        .catch(error => console.error('Error fetching facilities:', error));
        
    // Add click event for adding new facilities
    map.addListener('click', function(event) {
        const clickedLocation = event.latLng;
        
        // Show the add facility modal with coordinates
        showAddFacilityModal(clickedLocation.lat(), clickedLocation.lng());
    });
}

// Initialize map for tracking page
function initTrackingMap() {
    // This function will be used for real-time tracking
    // To be implemented when we have real-time data
}

// Calculate and display route between two points
function calculateAndDisplayRoute(origin, destination) {
    directionsService.route(
        {
            origin: origin,
            destination: destination,
            travelMode: google.maps.TravelMode.DRIVING
        },
        (response, status) => {
            if (status === 'OK') {
                directionsRenderer.setDirections(response);
            } else {
                console.error(`Directions request failed due to ${status}`);
            }
        }
    );
}

// Select a facility on the geofencing page
function selectFacility(facilityId) {
    // Update UI to show selected facility
    document.querySelectorAll('.facility-list-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const facilityItem = document.getElementById(`facility-${facilityId}`);
    if (facilityItem) {
        facilityItem.classList.add('active');
        
        // Fetch and display facility details
        fetch(`/geofencing/facility/${facilityId}`)
            .then(response => response.json())
            .then(facility => {
                document.getElementById('selected-facility-name').textContent = facility.name;
                document.getElementById('selected-facility-address').textContent = facility.address;
                document.getElementById('geofence-radius').value = facility.geofence_radius;
                document.getElementById('facility-id').value = facility.id;
                
                // Show the facility details panel
                document.getElementById('facility-details').classList.remove('d-none');
            })
            .catch(error => console.error('Error fetching facility details:', error));
    }
}

// Update facility geofence
function updateFacilityGeofence(facilityId, position, radius) {
    // Convert radius from meters to miles
    const radiusMiles = radius / 1609.34;
    
    // Update the radius input
    document.getElementById('geofence-radius').value = radiusMiles.toFixed(2);
    
    // Send update to server
    const data = {
        geofence_radius: radiusMiles,
        lat: position.lat(),
        lng: position.lng()
    };
    
    fetch(`/geofencing/facility/${facilityId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            console.log('Geofence updated successfully');
        } else {
            console.error('Error updating geofence:', result.error);
        }
    })
    .catch(error => console.error('Error:', error));
}

// Show modal for adding a new facility
function showAddFacilityModal(lat, lng) {
    const modal = new bootstrap.Modal(document.getElementById('add-facility-modal'));
    
    // Set the coordinates in the form
    document.getElementById('new-facility-lat').value = lat;
    document.getElementById('new-facility-lng').value = lng;
    
    // Get the address using reverse geocoding
    const geocoder = new google.maps.Geocoder();
    geocoder.geocode({ location: { lat, lng } }, (results, status) => {
        if (status === 'OK' && results[0]) {
            document.getElementById('new-facility-address').value = results[0].formatted_address;
        }
    });
    
    modal.show();
}

// Check if a vehicle is within a geofence
function checkGeofenceEntry(loadId, lat, lng) {
    const data = {
        load_id: loadId,
        lat: lat,
        lng: lng
    };
    
    return fetch('/geofencing/check', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json());
}

// Clean up map resources
function clearMap() {
    // Clear markers
    markers.forEach(marker => marker.setMap(null));
    markers = [];
    
    // Clear geofence circles
    geofenceCircles.forEach(circle => circle.setMap(null));
    geofenceCircles = [];
    
    // Clear directions
    if (directionsRenderer) {
        directionsRenderer.setMap(null);
    }
}
