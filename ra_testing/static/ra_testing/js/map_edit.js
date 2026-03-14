let map;
let markers = [];
let polyline;
let allPoints = [];

let undoStack = [];
const MAX_UNDO_STEPS = 50;

const BATCH_SIZE = 100;
let currentBatchIndex = 0;

let directionsService;
let directionsRenderer;
let markersToDelete = [];

let multiSelectEnabled = false;
let selectedMarkers = [];

const roadsApiKey = "AIzaSyCzmow8f_ZC9tyhaULB5xec8sG4HEchADk"; 
const directionsApiKey = "AIzaSyCzmow8f_ZC9tyhaULB5xec8sG4HEchADk"; 

let insertionIndex = null;

// Debounce function to limit API calls
function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        if (timeoutId) clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    }
}

// Caching snapped positions to optimize performance and reduce API call


const snappedCache = {};
function snapSingleMarkerToRoad(marker) {
    return new Promise((resolve, reject) => {
        const lat = marker.getPosition().lat().toFixed(5);
        const lng = marker.getPosition().lng().toFixed(5);
        const key = `${lat},${lng}`;

        if (snappedCache[key]) {
            marker.setPosition(snappedCache[key]);
            allPoints[marker.globalIndex] = {
                lat: snappedCache[key].lat,
                lng: snappedCache[key].lng,
                time: allPoints[marker.globalIndex].time
            };
            filesData[currentFileIndex].points[marker.globalIndex] = allPoints[marker.globalIndex];
            resolve();
            return;
        }

        // Construct the Roads API URL
        const url = `https://roads.googleapis.com/v1/snapToRoads?path=${lat},${lng}&key=${roadsApiKey}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.snappedPoints && data.snappedPoints.length > 0) {
                    const snappedPoint = data.snappedPoints[0].location;
                    const snappedPosition = {
                        lat: snappedPoint.latitude,
                        lng: snappedPoint.longitude
                    };
                    marker.setPosition(snappedPosition);

                    // Cache the snapped position
                    snappedCache[key] = snappedPosition;

                    // Update your allPoints and filesData arrays
                    allPoints[marker.globalIndex] = {
                        lat: snappedPoint.latitude,
                        lng: snappedPoint.longitude,
                        time: allPoints[marker.globalIndex].time
                    };

                    filesData[currentFileIndex].points[marker.globalIndex] = allPoints[marker.globalIndex];
                } else {
                    console.warn("No snapped points returned from Roads API.");
                }

                resolve();
            })
            .catch(error => {
                console.error("Error snapping marker to road:", error);
                reject(error);
            });
    });
}

/**
 * Snaps a segment of markers using the DirectionsService.
 * @param {Array<google.maps.Marker>} segmentMarkers - The markers in the segment to snap.
 * @returns {Promise} - Resolves when snapping is complete.
 */
function snapSegmentUsingDirectionsApi(segmentMarkers) {
    return new Promise((resolve, reject) => {
        if (!segmentMarkers || segmentMarkers.length < 2) {
            console.warn("Need at least two markers to snap a segment.");
            resolve();
            return;
        }

        const origin = segmentMarkers[0].getPosition();
        const destination = segmentMarkers[segmentMarkers.length - 1].getPosition();
        const waypoints = segmentMarkers.slice(1, -1).map(marker => ({
            location: marker.getPosition(),
            stopover: false
        }));

        const request = {
            origin: origin,
            destination: destination,
            waypoints: waypoints,
            travelMode: google.maps.TravelMode.DRIVING,
            optimizeWaypoints: false
        };

        directionsService.route(request, (result, status) => {
            if (status === google.maps.DirectionsStatus.OK) {
                const route = result.routes[0];
                const legs = route.legs;

                legs.forEach((leg, index) => {
                    const marker = segmentMarkers[index];
                    const snappedLocation = leg.start_location;
                    marker.setPosition(snappedLocation);

                    // Update your allPoints and filesData arrays
                    allPoints[marker.globalIndex] = {
                        lat: snappedLocation.lat(),
                        lng: snappedLocation.lng(),
                        time: allPoints[marker.globalIndex].time
                    };

                    filesData[currentFileIndex].points[marker.globalIndex] = allPoints[marker.globalIndex];
                });

                // Snap the last marker
                const lastLeg = legs[legs.length - 1];
                const lastMarker = segmentMarkers[segmentMarkers.length - 1];
                lastMarker.setPosition(lastLeg.end_location);
                allPoints[lastMarker.globalIndex] = {
                    lat: lastLeg.end_location.lat(),
                    lng: lastLeg.end_location.lng(),
                    time: allPoints[lastMarker.globalIndex].time
                };
                filesData[currentFileIndex].points[lastMarker.globalIndex] = allPoints[lastMarker.globalIndex];

                recalcPolyline();
                resolve();
            } else {
                console.warn('Directions request failed due to ' + status);
                reject(status);
            }
        });
    });
}

function handleMarkerClick(marker){
    if(multiSelectEnabled){
        if (selectedMarkers.length === 2 && !selectedMarkers.includes(marker)) {
            alert("Cannot select more than 2 markers at a time.");
            return; // Stop here
        }
        // console.log("Marker clicked:", marker);

        if (!selectedMarkers.includes(marker)) {
            selectedMarkers.push(marker);
            marker.setIcon({
                ...marker.getIcon(),
                fillColor: '#FF0000' 
            });
        } else {
            selectedMarkers = selectedMarkers.filter(m => m !== marker);
            marker.setIcon({
                ...marker.getIcon(),
                fillColor: '#00F'
            });
            console.log("Marker deselected:", marker);
        }

        if (selectedMarkers.length === 2) {
            console.log("Two markers selected. Adjusting points between them.");
            adjustPointsBetween(selectedMarkers[0], selectedMarkers[1]);
        }
    }
}

function adjustPointsBetween(marker1, marker2){
    const index1 = markers.indexOf(marker1);
    const index2 = markers.indexOf(marker2);

    if(index1 === -1 || index2 === -1) return;

    const startIndex = Math.min(index1, index2);
    const endIndex = Math.max(index1, index2);
    const segmentMarkers = markers.slice(startIndex, endIndex + 1);
    markersToDelete = markers.slice(startIndex + 1, endIndex);

    // Use Directions API to snap the segment
    snapSegmentUsingDirectionsApi(segmentMarkers)
        .then(() => {
            recalcPolyline();
        })
        .catch(error => {
            console.error("Error snapping segment using Directions API:", error);
        });
}


function handleUndo() {
    if (undoStack.length === 0) return;
    
    const lastAction = undoStack.pop();
    const { markerIndex, previousPosition } = lastAction;
    
    const marker = markers[markerIndex];
    if (marker) {
        marker.setPosition(previousPosition);
        snapSingleMarkerToRoad(marker)
            .then(() => {
                recalcPolyline();
            })
            .catch(error => {
                console.error("Error snapping marker during undo:", error);
            });
    }
    
    updateUndoButtonState();
}

function updateUndoButtonState() {
    const undoButton = document.getElementById('undoButton');
    if (undoButton) {
        undoButton.disabled = undoStack.length === 0;
    }
}

function pushToUndoStack(action) {
    undoStack.push(action);
    if (undoStack.length > MAX_UNDO_STEPS) {
        undoStack.shift();
    }
    updateUndoButtonState();
}

/**
 * Recalculates the polyline based on current marker positions.
 */
function recalcPolyline() {
    if (polyline) {
        polyline.setMap(null);
    }

    if (markers.length === 0) return;

    const path = markers.map(marker => marker.getPosition());

    polyline = new google.maps.Polyline({
        path: path,
        map: map,
        strokeColor: '#FF0000',
        strokeOpacity: 0.8,
        strokeWeight: 2
    });
}

function updateBatchInfo() {
    const startPoint = currentBatchIndex * BATCH_SIZE + 1;
    const endPoint = Math.min((currentBatchIndex + 1) * BATCH_SIZE, pointsData.length);
    const totalBatches = Math.ceil(pointsData.length / BATCH_SIZE);
    
    document.getElementById('batchInfo').textContent = 
        `Showing points ${startPoint}-${endPoint} of ${pointsData.length} (Batch ${currentBatchIndex + 1}/${totalBatches})`;
    
    document.getElementById('nextBatch').disabled = endPoint >= pointsData.length;
    document.getElementById('prevBatch').disabled = currentBatchIndex === 0;
}

function clearCurrentMarkers() {
    markers.forEach((marker) => {
        marker.setMap(null);
    });

    markers = [];
    if (polyline) {
        polyline.setMap(null);
    }
}

/**
 * Loads a batch of markers onto the map.
 * @param {number} batchIndex - The index of the batch to load.
 */
function loadBatch(batchIndex) {
    clearCurrentMarkers();
    currentBatchIndex = batchIndex;

    const start = currentBatchIndex * BATCH_SIZE;
    const end = Math.min(start + BATCH_SIZE, pointsData.length);

    let bounds = new google.maps.LatLngBounds();
    let hasValidPoints = false;

    const snappingPromises = [];

    for (let i = start; i < end; i++) {
        const point = allPoints[i];
        if (!point || !point.lat || !point.lng) {
            console.warn(`Invalid point data at index ${i}:`, point);
            continue;
        }

        const lat = parseFloat(point.lat);
        const lng = parseFloat(point.lng);
        if (isNaN(lat) || isNaN(lng)) {
            console.warn(`Invalid coordinates at index ${i}: lat=${point.lat}, lng=${point.lng}`);
            continue;
        }

        const position = { lat, lng };
        bounds.extend(position);
        hasValidPoints = true;

        const marker = new google.maps.Marker({
            position,
            map: map,
            draggable: true,
            icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 3,
                fillColor: '#00F',
                fillOpacity: 0.8,
                strokeWeight: 1
            },
            optimized: true
        });

        marker.index = i - start;
        marker.globalIndex = i;
        marker.addListener('click', () => handleMarkerClick(marker));

        marker.addListener('dragstart', () => {
            marker._lastPosition = marker.getPosition();
            if (markersToDelete.includes(marker)) {
                markersToDelete.forEach(m => {
                    m._lastPosition = m.getPosition();
                });
            }
        });

        marker.addListener('dragend', debounce((event) => {
            if (marker._lastPosition) {
                pushToUndoStack({
                    markerIndex: marker.index,
                    previousPosition: marker._lastPosition
                });
            }
            marker.setPosition(event.latLng);
            allPoints[marker.globalIndex] = {
                lat: event.latLng.lat(),
                lng: event.latLng.lng(),
                time: allPoints[marker.globalIndex].time
            };

            // Update the underlying file data
            filesData[currentFileIndex].points[marker.globalIndex] = allPoints[marker.globalIndex];

            if (markersToDelete.includes(marker)) {
                // If this marker is in markersToDelete, shift them together
                const oldPos = marker._lastPosition;
                const newPos = event.latLng;
                const latOffset = newPos.lat() - oldPos.lat();
                const lngOffset = newPos.lng() - oldPos.lng();
                markersToDelete.forEach(m => {
                    if (m !== marker) {
                        pushToUndoStack({
                            markerIndex: m.index,
                            previousPosition: m._lastPosition
                        });
                        const currentPos = m.getPosition();
                        const updatedLat = currentPos.lat() + latOffset;
                        const updatedLng = currentPos.lng() + lngOffset;
                        m.setPosition({ lat: updatedLat, lng: updatedLng });

                        allPoints[m.globalIndex] = {
                            lat: updatedLat,
                            lng: updatedLng,
                            time: allPoints[m.globalIndex].time
                        };
                        snappingPromises.push(snapSingleMarkerToRoad(m));
                    }
                });
                snappingPromises.push(snapSingleMarkerToRoad(marker));
                Promise.all(snappingPromises)
                    .then(() => {
                        recalcPolyline();
                    })
                    .catch(error => {
                        console.error("Error snapping markers during drag:", error);
                    });
            } else {
                // Determine if multi-select is active and use Directions API if so
                if (multiSelectEnabled && selectedMarkers.length === 2) {
                    snappingPromises.push(snapSegmentUsingDirectionsApi(selectedMarkers));
                    Promise.all(snappingPromises)
                        .then(() => {
                            recalcPolyline();
                        })
                        .catch(error => {
                            console.error("Error snapping segment during drag:", error);
                        });
                } else {
                    // Snap just the dragged marker, then re-draw
                    snappingPromises.push(snapSingleMarkerToRoad(marker));
                    Promise.all(snappingPromises)
                        .then(() => {
                            recalcPolyline();
                        })
                        .catch(error => {
                            console.error("Error snapping marker during drag:", error);
                        });
                }
            }
        }, 300)); // Debounce delay of 300ms

        markers.push(marker);

        // Initiate snapping and store promises
        snappingPromises.push(snapSingleMarkerToRoad(marker));
    }

    // Show raw polyline now (before snapping)
    recalcPolyline();

    if (hasValidPoints) {
        map.fitBounds(bounds);

        // After all markers are snapped, recalc the polyline
        Promise.all(snappingPromises)
            .then(() => {
                recalcPolyline();
            })
            .catch(error => {
                console.error("Error snapping markers during loadBatch:", error);
            });
    } else {
        recalcPolyline();
    }

    updateBatchInfo();
}

function nextBatch() {
    if ((currentBatchIndex + 1) * BATCH_SIZE < pointsData.length) {
        loadBatch(currentBatchIndex + 1);
    }
}

function previousBatch() {
    if (currentBatchIndex > 0) {
        loadBatch(currentBatchIndex - 1);
    }
}

function initMap() {
    allPoints = [...pointsData];

    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer({
        suppressMarkers: true,
        preserveViewport: true
    });

    let centerLatLng = { lat: 30.210995, lng: 74.945473 };
    if (pointsData && pointsData.length > 0) {
        for (let point of pointsData) {
            if (point && point.lat && point.lng) {
                const lat = parseFloat(point.lat);
                const lng = parseFloat(point.lng);
                if (!isNaN(lat) && !isNaN(lng)) {
                    centerLatLng = { lat, lng };
                    break;
                }
            }
        }
    }

    map = new google.maps.Map(document.getElementById('map'), {
        zoom: 14,
        center: centerLatLng,
        mapTypeId: google.maps.MapTypeId.ROADMAP,
        optimized: true,
        fullscreenControl: true,
        streetViewControl: false,
        mapTypeControl: true,
        mapTypeControlOptions: {
            style: google.maps.MapTypeControlStyle.HORIZONTAL_BAR,
            position: google.maps.ControlPosition.TOP_RIGHT
        },
        zoomControl: true,
        zoomControlOptions: {
            position: google.maps.ControlPosition.RIGHT_CENTER
        }
    });

    directionsRenderer.setMap(map);

    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
            e.preventDefault();
            handleUndo();
        }
    });

    document.getElementById('undoButton').addEventListener('click', handleUndo);
    document.getElementById('nextBatch').addEventListener('click', nextBatch);
    document.getElementById('prevBatch').addEventListener('click', previousBatch);
    document.getElementById('downloadSelectedButton').addEventListener('click', downloadUpdatedGPX);

    if (pointsData && pointsData.length > 0) {
        console.log("Loading first batch of points");
        loadBatch(0);
    } else {
        console.warn("No point data available");
    }

    document.getElementById('enableMultiSelect').addEventListener('change', (event) => {
        multiSelectEnabled = event.target.checked;
        if (!multiSelectEnabled) {
            selectedMarkers.forEach(m => {
                m.setIcon({ 
                    ...m.getIcon(),
                    fillColor: '#00F' 
                });
            });
            selectedMarkers = [];   
            markersToDelete = []; 
        }
        // console.log("Multi-select enabled:", multiSelectEnabled);
    });

    // Optional: Handle map clicks to add new markers
}

function downloadUpdatedGPX() {
    clearCurrentMarkers();
    const selectedIndex = parseInt(fileSelector.value);
    const selectedPoints = filesData[selectedIndex].points;
    const formData = new FormData();
    formData.append('points_json', JSON.stringify(selectedPoints));

    const csrftoken = getCookie('csrftoken');
    formData.append('csrfmiddlewaretoken', csrftoken);

    fetch(updateGpxUrl, {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) throw new Error(response.statusText);
        return response.blob();
    })
    .then(blob => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'updated_route.gpx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        loadBatch(currentBatchIndex);
    })
    .catch(error => {
        console.error('Error downloading GPX:', error);
        loadBatch(currentBatchIndex);
    });
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

window.onload = initMap;
