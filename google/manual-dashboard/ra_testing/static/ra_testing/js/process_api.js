// --- 1. Global Variables & Setup ---
function getCsrfToken() {
	const cookies = document.cookie.split(';');
	for (let i = 0; i < cookies.length; i++) {
		const cookie = cookies[i].trim();
		if (cookie.startsWith('csrftoken=')) {
			return decodeURIComponent(cookie.substring('csrftoken='.length));
		}
	}
	console.error('CSRF token not found in cookies!');
	return null;
}
let gpx_data = null;
const csrfToken = getCsrfToken();
// --- 2. On Load: Fetch GPX Data ---
document.addEventListener('DOMContentLoaded', function () {
	// Note: These elements must exist in your HTML
	const surveyIdEl = document.getElementById('surveyId');
	const roadIdEl = document.getElementById('roadId');
	const modelTypeEl = document.getElementById('categorySelect');

	const surveyId = surveyIdEl ? surveyIdEl.value : null;
	const roadId = roadIdEl ? roadIdEl.value : null;
	const modelType = modelTypeEl ? modelTypeEl.value : null;

	if (!surveyId || !roadId) return;

	fetch('/download-gpx/', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-CSRFToken': getCsrfToken(),
		},
		body: JSON.stringify({
			surveyId,
			roadId,
			modelType,
		}),
	})
		.then((response) => {
			if (response.ok) {
				return response.json();
			} else {
				throw new Error('Failed to fetch the JSON data.');
			}
		})
		.then((jsonData) => {
			gpx_data = jsonData;
			displayJsonData(jsonData);

			// timestamp ka saara seen idhr h
			const searchBox = document.getElementById('searchBox');
			if (searchBox) {
				// Fallback: If backend sent an empty timestamp, use the one from the 'Prev' button
				if (searchBox.value.trim() === '') {
					const prevButton =
						document.getElementById('prevImageButton');
					if (prevButton) {
						const prevTs = prevButton.dataset.ts; // Now correctly populated from HTML fix above
						if (prevTs) {
							searchBox.value = prevTs.slice(0, 16);
							console.log(
								'Using fallback timestamp from previous image:',
								prevTs
							);
						}
					}
				}
				// Trigger the search logic if we have any value
				if (searchBox.value.trim() !== '') {
					searchBox.dispatchEvent(new Event('input'));
				}
			}
		})
		.catch((error) => {
			console.error('Error:', error);
		});
});

// --- 3. JSON Display & Search Functions ---
function displayJsonData(data) {
	const container = document.getElementById('jsonContainer');
	if (!container) return;
	container.innerHTML = '';

	for (const [key, value] of Object.entries(data)) {
		const entryDiv = document.createElement('div');
		entryDiv.className = 'json-entry';
		entryDiv.innerHTML = `<strong>${key}</strong>: ${JSON.stringify(value, null, 2)}<br><br>`;
		entryDiv.addEventListener('click', () => {
			const searchBox = document.getElementById('searchBox');
			if (searchBox) {
				searchBox.value = key;
				searchBox.dispatchEvent(new Event('input'));
			}
		});
		container.appendChild(entryDiv);
	}

	container.style.overflowY = 'auto';
	container.style.width = '100%';
	addSearchFunctionality(data);
}

function addSearchFunctionality(data) {
	const searchBox = document.getElementById('searchBox');
	const container = document.getElementById('jsonContainer');
	if (!searchBox || !container) return;

	searchBox.addEventListener('input', () => {
		const searchTxt = searchBox.value.trim();
		container.innerHTML = '';

		if (searchTxt === '') {
			displayJsonData(data);
		} else {
			let found = false;
			const isDistSearch = searchTxt.toLowerCase().startsWith('dist=');
			const searchVal = isDistSearch
				? searchTxt.substring(5).trim()
				: searchTxt.toLowerCase();

			for (const [key, value] of Object.entries(data)) {
				let match = false;
				if (isDistSearch) {
					// Search in distanceInMeters
					const dist = value.distanceInMeters
						? value.distanceInMeters.toString()
						: '';
					if (dist.includes(searchVal)) {
						match = true;
					}
				} else {
					// Search in key (timestamp)
					if (key.toLowerCase().includes(searchVal)) {
						match = true;
					}
				}

				if (match) {
					found = true;
					const entryDiv = document.createElement('div');
					entryDiv.className = 'json-entry';

					let displayKey = key;
					if (!isDistSearch) {
						displayKey = key.replace(
							new RegExp(searchVal, 'gi'),
							(m) => `<span class="highlight">${m}</span>`,
						);
					}

					entryDiv.innerHTML = `<strong>${displayKey}</strong>: ${JSON.stringify(value, null, 2)}`;
					entryDiv.addEventListener('click', () => {
						const searchBox = document.getElementById('searchBox');
						if (searchBox) {
							searchBox.value = key;
							searchBox.dispatchEvent(new Event('input'));
						}
					});
					container.appendChild(entryDiv);
				}
			}
			if (!found) {
				container.innerHTML = `<div>No results found for "${searchTxt}".</div>`;
			}
		}
	});
}

// --- 4. Main Function: Collect & Send Anomalies ---
function collectAndSendAnomalies() {
	const anomalyContainers = document.querySelectorAll('.carousel-item');
	const modelType = document.getElementById('categorySelect').value;
	const finalPayload = {};

	if (modelType === 'pavement') {
		finalPayload.Anomalies = [];
	} else if (modelType === 'furniture') {
		finalPayload.assets = [];
		finalPayload.anomalies = [];
	}

	anomalyContainers.forEach((container) => {
		const category = container.dataset.category;
		const subcategory = container.dataset.subcategory;

		if (!category || !subcategory) return;
		if (category !== modelType) return;

		const config = CATEGORY_CONFIGS[category]?.[subcategory];
		if (!config) return;

		const boxIndex = parseInt(container.id.split('-')[1], 10);
		const itemData = {};

		Object.entries(config.fields).forEach(([fieldName, fieldConfig]) => {
			const fieldId = `${fieldName}-${boxIndex}`;
			const input = container.querySelector(`[name="${fieldId}"]`);

			if (input) {
				let value = input.value.trim();
				if (
					[
						'Latitude',
						'Longitude',
						'Distance',
						'Length',
						'Average width',
					].includes(fieldName)
				) {
					itemData[fieldName] =
						value === '' ? null : parseFloat(value);
				} else {
					itemData[fieldName] = value;
				}
			} else {
				itemData[fieldName] = null;
			}
		});

		if (subcategory === 'assets') {
			finalPayload.assets.push(itemData);
		} else if (subcategory === 'anomalies') {
			if (category === 'pavement') {
				finalPayload.Anomalies.push(itemData);
			} else if (category === 'furniture') {
				finalPayload.anomalies.push(itemData);
			}
		}
	});

	console.log(
		'Final JSON data being sent:',
		JSON.stringify(finalPayload, null, 2),
	);

	const surveyId = document.getElementById('surveyId').value;
	const roadId = document.getElementById('roadId').value;

	if (!csrfToken) return;

	fetch('/save-anomalies/', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			'X-CSRFToken': csrfToken,
		},
		body: JSON.stringify({
			surveyId,
			roadId,
			modelType,
			...finalPayload,
		}),
	})
		.then((response) => response.json())
		.then((data) => alert(data.message || 'Success!'))
		.catch((error) => {
			console.error('Error:', error);
			alert('Failed to save anomalies.');
		});
}

// --- 5. Image Upload Function (Helper) ---
// Note: We removed the listener for 'upload2s3' because the button was deleted.
function uploadImage(isFromAssets) {
	const canvas = document.getElementById('imageCanvas');
	const modelType = document.getElementById('categorySelect').value;
	const surveyId = document.getElementById('surveyId').value;
	const roadId = document.getElementById('roadId').value;

	// Ensure current_img_path is defined globally in your HTML
	const path =
		typeof current_img_path !== 'undefined' ? current_img_path : '';

	let fileName = path.split('/').pop().replace(/\s/g, '_');
	let originalFileName = path;
	let s3Folder = isFromAssets ? 'assets' : 'anomalies';

	console.log('S3 Path folder:', s3Folder);

	canvas.toBlob(function (blob) {
		const formData = new FormData();
		formData.append('image', blob, fileName);
		formData.append('surveyId', surveyId);
		formData.append('roadId', roadId);
		formData.append('modelType', modelType);
		formData.append('originalFileName', originalFileName);
		formData.append('s3Folder', s3Folder);

		fetch('/upload-s3/', {
			method: 'POST',
			headers: {
				'X-CSRFToken': getCsrfToken(),
			},
			body: formData,
		})
			.then((response) => response.json())
			.then((data) => alert(data.message))
			.catch((error) => {
				console.error('Error:', error);
				alert('Failed to upload image to S3.');
			});
	}, 'image/png');
}

// --- NEW FUNCTIONALITY: Convert Displayed Time by +5:30 AND UPLOAD ---

document
	.getElementById('convertDisplayedTimeBtn')
	.addEventListener('click', function () {
		// 1. Check if data exists
		if (!gpx_data || Object.keys(gpx_data).length === 0) {
			alert('No GPX Data currently loaded to convert.');
			return;
		}

		if (
			!confirm(
				'This will add 5 hours and 30 minutes to all timestamps, update the display, and OVERWRITE the file on the server. Continue?',
			)
		) {
			return;
		}

		const newData = {};
		let conversionCount = 0;

		// 2. Iterate through the existing data keys (timestamps) and convert
		for (const [timeKey, value] of Object.entries(gpx_data)) {
			try {
				// Check if key looks like a date (Simple check)
				if (timeKey.includes(':') && timeKey.includes('-')) {
					const parts = timeKey.split(' ');
					const dateParts = parts[0].split('-'); // [YYYY, MM, DD]
					const timeParts = parts[1].split(':'); // [HH, MM, SS]

					// Create date object
					const dateObj = new Date(
						dateParts[0],
						dateParts[1] - 1,
						dateParts[2],
						timeParts[0],
						timeParts[1],
						timeParts[2],
					);

					// Add 5 Hours and 30 Minutes
					dateObj.setHours(dateObj.getHours() + 5);
					dateObj.setMinutes(dateObj.getMinutes() + 30);

					// Format back to String: "YYYY-MM-DD HH:MM:SS"
					const year = dateObj.getFullYear();
					const month = String(dateObj.getMonth() + 1).padStart(
						2,
						'0',
					);
					const day = String(dateObj.getDate()).padStart(2, '0');
					const hour = String(dateObj.getHours()).padStart(2, '0');
					const min = String(dateObj.getMinutes()).padStart(2, '0');
					const sec = String(dateObj.getSeconds()).padStart(2, '0');

					const newKey = `${year}-${month}-${day} ${hour}:${min}:${sec}`;

					// Add to new object
					newData[newKey] = value;
					conversionCount++;
				} else {
					// If key isn't a timestamp, keep it as is
					newData[timeKey] = value;
				}
			} catch (e) {
				console.error('Error parsing date:', timeKey, e);
				newData[timeKey] = value; // Keep original on error
			}
		}

		// 3. Update global variable and refresh UI immediately
		gpx_data = newData;
		displayJsonData(gpx_data);

		// --- 4. PREPARE FOR UPLOAD ---
		console.log('Preparing to upload converted data...');

		// Convert the new JS object back to a JSON string
		const jsonString = JSON.stringify(newData, null, 4);

		// Create a Blob (acts like a file)
		const blob = new Blob([jsonString], { type: 'application/json' });

		// Prepare FormData
		const formData = new FormData();
		// 'gpxJson' is the key your Django view expects
		formData.append('gpxJson', blob, 'converted_gpx_data.json');

		// IMPORTANT: Send 'false' for add_time_offset because we ALREADY calculated it here in JS.

		formData.append('add_time_offset', 'false');

		// Get IDs
		const surveyId = document.getElementById('surveyId').value;
		const roadId = document.getElementById('roadId').value;
		const modelType = document.getElementById('categorySelect').value;

		// --- 5. PERFORM UPLOAD ---
		fetch(`/upload-json/${surveyId}/${roadId}/${modelType}/`, {
			method: 'POST',
			body: formData,
			headers: {
				'X-CSRFToken': getCsrfToken(),
			},
		})
			.then((response) => response.json())
			.then((data) => {
				if (data.message) {
					alert(
						`Success! Times converted locally (${conversionCount} entries) and saved to server successfully.`,
					);
					// Optional: window.location.reload();
				} else {
					alert(
						'Times converted locally, BUT server upload failed: ' +
							(data.error || 'Unknown error'),
					);
				}
			})
			.catch((error) => {
				console.error('Error uploading converted data:', error);
				alert('Times converted locally, BUT server upload failed.');
			});
	});

// --- 6. PATCH JSON TO DASHBOARD (VIA PROXY UPLOAD) ---
document.addEventListener('DOMContentLoaded', function () {
	const patchBtn = document.getElementById('patchJsonBtn');

	if (patchBtn) {
		console.log('Patch Button found! Attaching event listener...');

		patchBtn.addEventListener('click', function () {
			// 1. Get Data
			const surveyId = document.getElementById('surveyId').value;
			const roadId = document.getElementById('roadId').value;
			const modelType = document.getElementById('categorySelect').value;

			// Get Environment
			const envSelect = document.getElementById('environment');
			let targetSubdomain = envSelect ? envSelect.value : null;

			// Fallback to global variable if dropdown is empty/hidden
			if (!targetSubdomain && typeof subdomain !== 'undefined') {
				targetSubdomain = subdomain;
			}

			if (!targetSubdomain) {
				alert('Error: Could not determine Environment (Subdomain).');
				return;
			}

			const baseUrl = `https://${targetSubdomain}.roadathena.com`;

			if (
				!confirm(
					`Are you sure you want to patch Road ID ${roadId} to:\n${baseUrl}?`,
				)
			) {
				return;
			}

			console.log('Step 1: Fetching merged JSON blob locally...');

			// 2. Fetch the JSON Blob locally (Existing logic)
			fetch(`/merge-json/${surveyId}/${roadId}/${modelType}/`, {
				method: 'GET',
			})
				.then((response) => {
					if (!response.ok)
						throw new Error(
							`Local Merge Failed: ${response.statusText}`,
						);
					return response.blob();
				})
				.then((blob) => {
					console.log('Step 2: Sending Blob to Local Proxy...');

					// 3. Send the Blob to your Local Django Proxy
					const formData = new FormData();
					formData.append(
						'file_payload',
						blob,
						`merged_${roadId}.json`,
					); // The File
					formData.append('roadId', roadId);
					formData.append('subdomain', targetSubdomain);
					formData.append('modelType', modelType);

					return fetch('/proxy-patch-dashboard/', {
						method: 'POST',
						headers: {
							'X-CSRFToken': getCsrfToken(), // Django CSRF
						},
						body: formData, // Browser sets Content-Type to multipart/form-data automatically
					});
				})
				.then((response) => response.json())
				.then((data) => {
					if (data.message) {
						console.log('Success:', data.message);
						alert(data.message);
					} else {
						console.error('Server Error:', data);
						throw new Error(
							data.error || 'Unknown error from server',
						);
					}
				})
				.catch((error) => {
					console.error('Patch Process Error:', error);
					alert(`Failed: ${error.message}`);
				});
		});
	}
});

// --- 7. Download Manual JSON ---
document
	.getElementById('downloadJsonButton')
	.addEventListener('click', function () {
		const surveyId = document.getElementById('surveyId').value;
		const roadId = document.getElementById('roadId').value;
		const modelType = document.getElementById('categorySelect').value;

		fetch(`/download-json/${surveyId}/${roadId}/${modelType}/`, {
			method: 'GET',
		})
			.then((response) => response.blob())
			.then((blob) => {
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `manual_${roadId}.json`;
				document.body.appendChild(a);
				a.click();
				a.remove();
			})
			.catch((error) => {
				console.error('Error:', error);
				alert('Failed to download the JSON file.');
			});
	});

// --- 8. Delete JSON ---
document.getElementById('deleteJson').addEventListener('click', function () {
	const modelType = document.getElementById('categorySelect').value;
	const surveyId = document.getElementById('surveyId').value;
	const roadId = document.getElementById('roadId').value;

	fetch(`/delete-json/${surveyId}/${roadId}/${modelType}/`, {
		method: 'DELETE',
		headers: { 'X-CSRFToken': getCsrfToken() },
	})
		.then((response) => response.json())
		.then((data) => {
			if (data.message) alert(data.message);
			else alert(data.error);
		})
		.catch((error) => {
			console.error('Error:', error);
			alert('Failed to delete the JSON file.');
		});
});

// --- 9. Download Merged JSON ---
document
	.getElementById('downloadMergedJson')
	.addEventListener('click', function () {
		const surveyId = document.getElementById('surveyId').value;
		const roadId = document.getElementById('roadId').value;
		const modelType = document.getElementById('categorySelect').value;

		fetch(`/merge-json/${surveyId}/${roadId}/${modelType}/`, {
			method: 'GET',
		})
			.then((response) => response.blob())
			.then((blob) => {
				const url = window.URL.createObjectURL(blob);
				const a = document.createElement('a');
				a.href = url;
				a.download = `merged_${roadId}.json`;
				document.body.appendChild(a);
				a.click();
				a.remove();
			})
			.catch((error) => {
				console.error('Error:', error);
				alert('Failed to download the JSON file.');
			});
	});

// --- UPLOAD GPX JSON WITH TIME OFFSET ---
document.getElementById('uploadGpxJson').addEventListener('click', function () {
	const surveyId = document.getElementById('surveyId').value;
	const roadId = document.getElementById('roadId').value;
	const modelType = document.getElementById('categorySelect').value;

	const fileInput = document.getElementById('gpxJson');
	const file = fileInput.files[0];

	// 1. Check if the +5:30 box is ticked
	const addOffset = document.getElementById('addTimeOffset').checked;

	if (!file) {
		alert('Please select a file to upload.');
		return;
	}

	const formData = new FormData();
	formData.append('gpxJson', file);
	// 2. Send the status to the backend
	formData.append('add_time_offset', addOffset);

	fetch(`/upload-json/${surveyId}/${roadId}/${modelType}/`, {
		method: 'POST',
		body: formData,
		headers: {
			'X-CSRFToken': getCsrfToken(),
		},
	})
		.then((response) => response.json())
		.then((data) => {
			if (data.message) {
				alert('File uploaded successfully!');
				window.location.reload();
			} else {
				alert('Failed to upload: ' + (data.error || 'Unknown error'));
			}
		})
		.catch((error) => {
			console.error('Error:', error);
			alert('Failed to upload the file.');
		});
});
