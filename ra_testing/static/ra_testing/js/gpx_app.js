// Debug logging
console.log('GPX App JS loading...');

let map;

// An array of "roads". Each road is an object:
// {
//   points: [google.maps.LatLng, ...],
//   markers: [google.maps.Marker, ...],
//   distanceLabels: [google.maps.Marker, ...],
//   polyline: google.maps.Polyline
// }
let roads = [];

// This points to the "active" road index in the roads array
let currentRoadIndex = 0;

let undoStack = [];
const MAX_UNDO_STEPS = 50; // Maximum number of undo steps to store

// Add this new function to handle undo operations
function handleUndo() {
  if (undoStack.length === 0) return;

  const lastAction = undoStack.pop();
  const { roadIndex, markerIndex, previousPosition } = lastAction;

  // Get the marker and update its position
  const marker = roads[roadIndex].markers[markerIndex];
  if (marker) {
    marker.setPosition(previousPosition);
    roads[roadIndex].points[markerIndex] = previousPosition;
    recalcRoad(roadIndex);
  }

  // Update undo button state
  updateUndoButtonState();
}

// Add this function to update the undo button state
function updateUndoButtonState() {
  const undoButton = document.getElementById('undoButton');
  if (undoButton) {
    undoButton.disabled = undoStack.length === 0;
  }
}

// Add this function to push actions to the undo stack
function pushToUndoStack(action) {
  undoStack.push(action);
  if (undoStack.length > MAX_UNDO_STEPS) {
    undoStack.shift(); // Remove oldest action if we exceed max steps
  }
  updateUndoButtonState();
}

const tableBody = document.querySelector('#roadsTable tbody');
function populateTable(data) {
  tableBody.innerHTML = '';

  data.forEach((road, index) => {
    const row = document.createElement('tr');

    // Road Name Cell
    const nameCell = document.createElement('td');
    nameCell.textContent = road.name;
    row.appendChild(nameCell);

    // Download Cell
    const downloadCell = document.createElement('td');

    const downloadButton = document.createElement('button');
    downloadButton.textContent = 'Download';
    downloadButton.classList.add('download-btn');

    // **Associate the button with the road's index**
    downloadButton.setAttribute('data-road-index', index);

    // **Add event listener with road index**
    downloadButton.addEventListener("click", () => downloadGPX(index));

    downloadCell.appendChild(downloadButton);
    row.appendChild(downloadCell);

    tableBody.appendChild(row);
  });

}

// // Populate the table on page load
// document.addEventListener('DOMContentLoaded', () => {
//   populateTable(roads);
// });

function initMap() {
  console.log('Initializing map...');

  map = new google.maps.Map(document.getElementById("map"), {
    center: { lat: 20, lng: 0 },
    zoom: 2,
  });

  console.log('Map initialized:', map);

  // Click on the map adds a marker to the current (active) road
  map.addListener("click", (e) => onMapClick(e.latLng));

  // "Next Road" button
  const roadNameInput = document.getElementById('roadName');
  console.log('Road name input found:', roadNameInput);

  const nextRoadButton = document.getElementById('nextRoad');
  console.log('Next road button found:', nextRoadButton);

  if (nextRoadButton) {
    nextRoadButton.addEventListener("click", () => {
      const roadName = roadNameInput.value.trim();
      console.log('Starting new road with name:', roadName);
      finalizeCurrentRoad();
      startNewRoad(roadName);
      updateResultMessage();
    });
  }

  // Add download button listener
  const downloadButton = document.getElementById('download');
  if (downloadButton) {
    downloadButton.addEventListener("click", () => {
      if (roads.length === 0) {
        alert("Please create a road first before downloading.");
        return;
      }
      // Download the current/last road
      downloadGPX(currentRoadIndex);
    });
  }

  updateResultMessage();
  updateUndoButtonState();

  // Add keyboard event listener for Ctrl+Z
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
      e.preventDefault(); // Prevent browser's default undo
      handleUndo();
    }
  });

  // Add undo button click listener
  const undoButton = document.getElementById('undoButton');
  if (undoButton) {
    undoButton.addEventListener('click', handleUndo);
  }

  console.log('Map initialization complete');
}

function startNewRoad(roadName) {

  const newPolyline = new google.maps.Polyline({
    map: map,
    path: [],
    strokeColor: "red",
    strokeOpacity: 1.0,
    strokeWeight: 12,
  });

  const newRoad = {
    points: [],
    markers: [],
    distanceLabels: [],
    polyline: newPolyline,
    name: roadName,
    file: `${roadName.replace(/\s+/g, '_').toLowerCase()}.gpx`
  };
  roads.push(newRoad);
  currentRoadIndex = roads.length - 1;
  populateTable(roads)
}

/**
 * Optionally do something to "finalize" the current road.
 * For now, we just change the polyline color to indicate it's finalized.
 */
function finalizeCurrentRoad() {

}

/**
 * Handle map click to add a marker to the current (active) road.
 * @param {google.maps.LatLng} latLng The clicked location.
 */
function onMapClick(latLng) {

  if (roads.length === 0) {
    alert("Please add a road by providing a road name first.");
    return; // Exit if no roads are present
  }

  const activeRoad = roads[currentRoadIndex];
  const marker = new google.maps.Marker({
    position: latLng,
    map: map,
    draggable: true,
  });

  // Store the marker's initial position for undo
  const markerIndex = activeRoad.markers.length;

  activeRoad.markers.push(marker);
  activeRoad.points.push(latLng);

  // Add drag start listener to store the position before dragging
  marker.addListener("dragstart", function (e) {
    marker._lastPosition = marker.getPosition();
  });

  marker.addListener("dragend", function (e) {
    if (marker._lastPosition) {
      pushToUndoStack({
        roadIndex: currentRoadIndex,
        markerIndex: activeRoad.markers.indexOf(marker),
        previousPosition: marker._lastPosition
      });
    }
    recalcRoad(currentRoadIndex);
  });

  marker.addListener("drag", function () {
    recalcRoad(currentRoadIndex);
  });

  marker.addListener("click", () => {
    const markerIndex = activeRoad.markers.indexOf(marker);
    if (markerIndex !== -1) {
      pushToUndoStack({
        roadIndex: currentRoadIndex,
        markerIndex: markerIndex,
        previousPosition: marker.getPosition()
      });
    }
    removeMarker(marker, currentRoadIndex);
  });

  recalcRoad(currentRoadIndex);
  updateResultMessage();
}

/**
 * Remove a marker from the given roadIndex.
 * @param {google.maps.Marker} marker The marker to remove.
 * @param {number} roadIndex The index of the road in the roads array.
 */
function removeMarker(marker, roadIndex) {
  const road = roads[roadIndex];
  const idx = road.markers.indexOf(marker);
  if (idx !== -1) {
    // Remove from map
    marker.setMap(null);
    // Remove from arrays
    road.markers.splice(idx, 1);
    road.points.splice(idx, 1);
    // Recalculate
    recalcRoad(roadIndex);
  }
  updateResultMessage();
}

/**
 * Recalculate the polyline and distance labels for a specific road.
 * @param {number} roadIndex The index of the road.
 */
function recalcRoad(roadIndex) {
  try {
    const road = roads[roadIndex];

    // 1) Update the polyline path
    road.polyline.setPath(road.points);

    // 2) Remove existing distance labels for that road
    road.distanceLabels.forEach((label) => label.setMap(null));
    road.distanceLabels = [];

    // 3) If fewer than 2 points, there's no distance to measure
    if (road.points.length < 2) return;

    // 4) Calculate segment distances
    for (let i = 0; i < road.points.length - 1; i++) {
      const pointA = road.points[i];
      const pointB = road.points[i + 1];

      // Distance in meters
      const distanceInMeters = google.maps.geometry.spherical.computeDistanceBetween(
        pointA,
        pointB
      );
      const distanceInKm = (distanceInMeters / 1000).toFixed(2);

      // Midpoint for the label
      const midpoint = getMidpoint(pointA, pointB);

      // Create an invisible marker with label
      const labelMarker = new google.maps.Marker({
        position: midpoint,
        map: map,
        draggable: true,
        icon: {
          path: google.maps.SymbolPath.CIRCLE,
          scale: 5, // invisible
        },
        label: {
          text: `${distanceInKm} km`,
          color: "#00f",
          fontSize: "12px",
          fontWeight: "bold",
          fillOpacity: 0.8,
          strokeWeight: 2,
          strokeColor: "#00f"
        },
        clickable: false,
      });

      road.distanceLabels.push(labelMarker);

      midpointMarker.addListener("drag", function () {
        recalcRoad();
      });
    }
  } catch (error) {
    console.error(`Error recalculating road at index ${roadIndex}:`, error);
  }
}

/**
 * Update the "result" <div> with a brief status message.
 */
function updateResultMessage() {
  const resultDiv = document.getElementById("result");
  const activeRoad = roads[currentRoadIndex];
  const count = activeRoad.points.length;

  if (count === 0 && roads.length === 1) {
    resultDiv.textContent = "Click the map to place the first marker on the first road.";
    return;
  } else if (count === 0) {
    // If the active road is empty but there are previous roads
    resultDiv.textContent = `Road ${currentRoadIndex + 1} is empty. Click on the map to start adding markers.`;
    return;
  } else if (count === 1) {
    resultDiv.textContent = `First marker placed on Road ${currentRoadIndex + 1}. Click again to draw a segment.`;
    return;
  } else {
    // More than 1 point
    resultDiv.textContent = `Road ${currentRoadIndex + 1} has ${count} markers.`;
  }
}

/**
 * Calculate the midpoint between two LatLng points.
 * @param {google.maps.LatLng} pointA The first point.
 * @param {google.maps.LatLng} pointB The second point.
 * @returns {google.maps.LatLng} The midpoint LatLng.
 */
function getMidpoint(pointA, pointB) {
  const lat = (pointA.lat() + pointB.lat()) / 2;
  const lng = (pointA.lng() + pointB.lng()) / 2;
  return new google.maps.LatLng(lat, lng);
}

/**
 * Retrieve the CSRF token (if needed for Django).
 * Adjust as appropriate for your setup.
 */
function getCSRFToken() {
  const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
  return csrfToken ? csrfToken.value : '';
}

/**
 * Download the entire set of roads as a GPX file.
 * @param {Event} event The click event.
 */
function downloadGPX(roadIndex) {
  const road = roads[roadIndex];
  const csrfToken = getCSRFToken();

  if (!csrfToken) {
    console.error('CSRF token not found');
    alert('Error: Security token not found. Please refresh the page and try again.');
    return;
  }

  // Prepare data for the specific road
  const roadData = {
    name: road.name || `road_${roadIndex + 1}`, // Assign default name if none
    points: road.points.map((p) => ({ lat: p.lat(), lng: p.lng() }))
  };

  console.log("Downloading road:", roadData);

  const payload = { road: roadData }; // Wrap in 'road' key

  fetch("/gpx-app/download-gpx/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: JSON.stringify(payload),
    credentials: 'same-origin'  // Important for CSRF
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then((err) => { throw new Error(err.error || "Network response was not OK"); });
      }
      return response.json(); // Expect JSON with gpx_file
    })
    .then((data) => {
      if (data.gpx_file) { // Expect a single file object
        const file = data.gpx_file;

        // Decode Base64 string to binary data
        const binaryString = atob(file.data);
        const byteNumbers = new Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          byteNumbers[i] = binaryString.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);

        // Create a Blob from the byte array
        const blob = new Blob([byteArray], { type: "application/gpx+xml" });

        // Create a temporary URL for the Blob
        const url = window.URL.createObjectURL(blob);

        // Create a temporary <a> element
        const link = document.createElement("a");
        link.href = url;
        link.download = file.filename; // Use the provided filename

        // Append the link to the body
        document.body.appendChild(link);

        // Programmatically click the link to trigger the download
        link.click();

        // Remove the link from the document
        document.body.removeChild(link);

        // Revoke the Blob URL to free up memory
        window.URL.revokeObjectURL(url);
      } else {
        throw new Error("Invalid response structure.");
      }

    })
    .catch((error) => {
      console.error("Error downloading GPX:", error);
      alert(error.message);
    });
}

// Initialize the map when the window loads
window.addEventListener('load', () => {
  console.log('Window loaded, initializing map...');
  initMap();
});




