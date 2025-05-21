// Real-time tracking functionality
let trackingMap;
let trackingMarkers = {};
let trackingInterval;
let activeLoads = {};
let trackingRoutes = {};

// Initialize tracking functionality
function initializeTracking() {
    // Check if we're on a tracking-enabled page
    const trackingContainer = document.getElementById('tracking-container');
    if (!trackingContainer) return;
    
    // Load active loads
    loadActiveLoads();
    
    // Set up refresh interval (every 30 seconds)
    trackingInterval = setInterval(updateVehiclePositions, 30000);
    
    // Initial position update
    updateVehiclePositions();
}

// Load all active loads
function loadActiveLoads() {
    fetch('/loads/data?status=in_transit')
        .then(response => response.json())
        .then(data => {
            if (!data || !data.loads) return;
            
            // Store active loads data
            data.loads.forEach(load => {
                activeLoads[load.id] = load;
            });
            
            // Update the tracking list
            updateTrackingList();
        })
        .catch(error => console.error('Error loading active loads:', error));
}

// Update the list of tracked loads
function updateTrackingList() {
    const trackingList = document.getElementById('tracking-list');
    if (!trackingList) return;
    
    trackingList.innerHTML = '';
    
    if (Object.keys(activeLoads).length === 0) {
        trackingList.innerHTML = '<div class="list-group-item">No active loads to track</div>';
        return;
    }
    
    for (const loadId in activeLoads) {
        const load = activeLoads[loadId];
        
        const listItem = document.createElement('a');
        listItem.href = '#';
        listItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
        listItem.setAttribute('data-load-id', loadId);
        listItem.onclick = function(e) {
            e.preventDefault();
            selectLoadForTracking(loadId);
        };
        
        listItem.innerHTML = `
            <div>
                <strong>${load.reference_number}</strong>
                <div class="text-muted small">${load.driver}</div>
            </div>
            <div class="text-end">
                <div>${formatDeliveryTime(load.scheduled_delivery)}</div>
                <div class="small ${getETAClass(load.current_eta, load.scheduled_delivery)}">
                    ETA: ${formatTime(load.current_eta)}
                </div>
            </div>
        `;
        
        trackingList.appendChild(listItem);
    }
}

// Update vehicle positions for active loads
function updateVehiclePositions() {
    for (const loadId in activeLoads) {
        // In a real application, we would fetch the real-time position from the Motive API
        // For demonstration, we'll simulate movement with random positions
        // This would be replaced with actual API calls
        simulateVehicleMovement(loadId);
    }
}

// Simulate vehicle movement (for demo purposes)
function simulateVehicleMovement(loadId) {
    const load = activeLoads[loadId];
    if (!load) return;
    
    // This is a simplified simulation - in a real app, you would fetch actual position data
    fetch(`/loads/${loadId}/data`)
        .then(response => response.json())
        .then(data => {
            if (!data || !data.last_locations || data.last_locations.length === 0) return;
            
            const lastLocation = data.last_locations[0];
            const position = {
                lat: lastLocation.lat,
                lng: lastLocation.lng
            };
            
            // Update marker position
            updateVehicleMarker(loadId, position, data);
            
            // Check geofence entry/exit
            checkGeofenceEntry(loadId, position.lat, position.lng)
                .then(result => {
                    if (result.status_changed) {
                        showNotification(`Vehicle ${result.entry_exit === 'entry' ? 'entered' : 'exited'} ${result.facility_type} facility for load #${data.reference_number}`, 'info');
                        
                        // Refresh load data
                        loadActiveLoads();
                    }
                })
                .catch(error => console.error('Error checking geofence:', error));
        })
        .catch(error => console.error(`Error fetching load data for ${loadId}:`, error));
}

// Update vehicle marker on the map
function updateVehicleMarker(loadId, position, loadData) {
    if (!trackingMap) return;
    
    // Create marker if it doesn't exist
    if (!trackingMarkers[loadId]) {
        const marker = new google.maps.Marker({
            position: position,
            map: trackingMap,
            title: `Load #${loadData.reference_number}`,
            icon: {
                url: 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                scaledSize: new google.maps.Size(32, 32)
            },
            animation: google.maps.Animation.DROP
        });
        
        trackingMarkers[loadId] = marker;
        
        // Add info window
        const infoWindow = new google.maps.InfoWindow({
            content: createInfoWindowContent(loadData)
        });
        
        marker.addListener('click', () => {
            infoWindow.open(trackingMap, marker);
        });
    } else {
        // Update existing marker position
        trackingMarkers[loadId].setPosition(position);
    }
    
    // Update route if this is the selected load
    const selectedLoadId = document.querySelector('.tracking-load.active')?.dataset.loadId;
    if (selectedLoadId && selectedLoadId === loadId) {
        updateTrackingRoute(loadId, position);
    }
}

// Update the route for a tracked load
function updateTrackingRoute(loadId, currentPosition) {
    const load = activeLoads[loadId];
    if (!load || !trackingMap) return;
    
    // Get load details
    fetch(`/loads/${loadId}/data`)
        .then(response => response.json())
        .then(data => {
            if (!data || !data.delivery || !data.delivery.lat || !data.delivery.lng) return;
            
            // Create directions service if needed
            if (!directionsService) {
                directionsService = new google.maps.DirectionsService();
            }
            
            // Create directions renderer if needed
            if (!trackingRoutes[loadId]) {
                trackingRoutes[loadId] = new google.maps.DirectionsRenderer({
                    map: trackingMap,
                    suppressMarkers: true,
                    polylineOptions: {
                        strokeColor: '#3F51B5',
                        strokeOpacity: 0.7,
                        strokeWeight: 5
                    }
                });
            }
            
            // Calculate and display route
            directionsService.route(
                {
                    origin: currentPosition,
                    destination: { lat: data.delivery.lat, lng: data.delivery.lng },
                    travelMode: google.maps.TravelMode.DRIVING
                },
                (response, status) => {
                    if (status === 'OK') {
                        trackingRoutes[loadId].setDirections(response);
                        
                        // Update ETA based on route
                        const route = response.routes[0];
                        const leg = route.legs[0];
                        const etaSeconds = leg.duration.value;
                        const now = new Date();
                        const eta = new Date(now.getTime() + etaSeconds * 1000);
                        
                        // Update ETA in the UI
                        document.getElementById('selected-load-eta').textContent = formatDateTime(eta);
                        
                        // Check if the ETA is after the scheduled delivery time
                        const scheduledDelivery = new Date(data.delivery.scheduled_time);
                        if (eta > scheduledDelivery) {
                            const lateBy = Math.round((eta - scheduledDelivery) / (60 * 1000)); // minutes late
                            document.getElementById('selected-load-status').textContent = `Running Late: ~${lateBy} min`;
                            document.getElementById('selected-load-status').className = 'text-danger';
                        } else {
                            document.getElementById('selected-load-status').textContent = 'On Time';
                            document.getElementById('selected-load-status').className = 'text-success';
                        }
                        
                        // Update distance and time remaining
                        document.getElementById('selected-load-distance').textContent = leg.distance.text;
                        document.getElementById('selected-load-time').textContent = leg.duration.text;
                    } else {
                        console.error(`Directions request failed: ${status}`);
                    }
                }
            );
        })
        .catch(error => console.error('Error getting load details:', error));
}

// Select a load for detailed tracking
function selectLoadForTracking(loadId) {
    // Update UI to show selected load
    document.querySelectorAll('.list-group-item').forEach(item => {
        item.classList.remove('active');
    });
    
    document.querySelector(`.list-group-item[data-load-id="${loadId}"]`).classList.add('active');
    
    // Show the details panel
    document.getElementById('tracking-details').classList.remove('d-none');
    
    // Get load details
    fetch(`/loads/${loadId}/data`)
        .then(response => response.json())
        .then(data => {
            // Update load details display
            document.getElementById('selected-load-ref').textContent = data.reference_number;
            document.getElementById('selected-load-driver').textContent = data.driver ? data.driver.name : 'Unassigned';
            document.getElementById('selected-load-pickup').textContent = data.pickup ? data.pickup.name : 'Unknown';
            document.getElementById('selected-load-delivery').textContent = data.delivery ? data.delivery.name : 'Unknown';
            document.getElementById('selected-load-scheduled').textContent = formatDateTime(data.delivery.scheduled_time);
            document.getElementById('selected-load-eta').textContent = formatDateTime(data.current_eta);
            
            // Check and display on-time status
            if (data.current_eta && data.delivery && data.delivery.scheduled_time) {
                const eta = new Date(data.current_eta);
                const scheduledDelivery = new Date(data.delivery.scheduled_time);
                
                if (eta > scheduledDelivery) {
                    const lateBy = Math.round((eta - scheduledDelivery) / (60 * 1000)); // minutes late
                    document.getElementById('selected-load-status').textContent = `Running Late: ~${lateBy} min`;
                    document.getElementById('selected-load-status').className = 'text-danger';
                } else {
                    document.getElementById('selected-load-status').textContent = 'On Time';
                    document.getElementById('selected-load-status').className = 'text-success';
                }
            } else {
                document.getElementById('selected-load-status').textContent = 'Status Unknown';
                document.getElementById('selected-load-status').className = 'text-muted';
            }
            
            // If we have last location and tracking map, center on vehicle
            if (data.last_locations && data.last_locations.length > 0 && trackingMap) {
                const position = {
                    lat: data.last_locations[0].lat,
                    lng: data.last_locations[0].lng
                };
                
                // Center map on vehicle
                trackingMap.setCenter(position);
                trackingMap.setZoom(10);
                
                // Update the vehicle marker
                updateVehicleMarker(loadId, position, data);
                
                // Update the route
                updateTrackingRoute(loadId, position);
            }
        })
        .catch(error => console.error('Error getting load details:', error));
}

// Create content for the info window
function createInfoWindowContent(loadData) {
    return `
        <div class="info-window">
            <h5>Load #${loadData.reference_number}</h5>
            <p><strong>Driver:</strong> ${loadData.driver ? loadData.driver.name : 'Unassigned'}</p>
            <p><strong>Status:</strong> ${loadData.status}</p>
            <p><strong>Delivery:</strong> ${formatDateTime(loadData.delivery.scheduled_time)}</p>
            <p><strong>ETA:</strong> ${formatDateTime(loadData.current_eta)}</p>
            <a href="/loads/${loadData.id}" class="btn btn-sm btn-primary">View Details</a>
        </div>
    `;
}

// Format delivery time string
function formatDeliveryTime(timeStr) {
    if (!timeStr) return 'No delivery time';
    
    const date = new Date(timeStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Format time only
function formatTime(timeStr) {
    if (!timeStr) return 'N/A';
    
    const date = new Date(timeStr);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Get CSS class for ETA comparison
function getETAClass(etaStr, scheduledStr) {
    if (!etaStr || !scheduledStr) return '';
    
    const eta = new Date(etaStr);
    const scheduled = new Date(scheduledStr);
    
    if (eta > scheduled) {
        // If ETA is more than 30 minutes late
        if ((eta - scheduled) > 30 * 60 * 1000) {
            return 'text-danger';
        }
        // If ETA is less than 30 minutes late
        return 'text-warning';
    }
    
    return 'text-success';
}

// Clean up tracking resources
function cleanupTracking() {
    if (trackingInterval) {
        clearInterval(trackingInterval);
    }
    
    for (const loadId in trackingMarkers) {
        trackingMarkers[loadId].setMap(null);
    }
    
    for (const loadId in trackingRoutes) {
        if (trackingRoutes[loadId]) {
            trackingRoutes[loadId].setMap(null);
        }
    }
    
    trackingMarkers = {};
    trackingRoutes = {};
    activeLoads = {};
}

// Format date and time
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return 'N/A';
    
    const date = new Date(dateTimeStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Initialize tracking when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeTracking);
