const canvas = document.getElementById('imageCanvas');
const ctx = canvas.getContext('2d');
const editButton = document.getElementById('editImageButton');
const downloadButton = document.getElementById('downloadImageButton');
const undoButton = document.getElementById('undoBoundingBox');
const resolutionSelect = document.getElementById('resolutionSelect');
let currentCarouselIndex = 0;
let currentTrackIdColor = '#0dff00'; // Default color for TrackID label, change this
const trackIdDotRadius = 4; // Configurable radius for the central dot

// Cache for DOM elements to avoid repeated queries
const DOM_CACHE = {
	container: null,
	carouselContainer: null,
	itemsWrapper: null,
};

// NEW: Store editing session data
const EDITING_SESSION = {
	timestamp: null,
	locationData: null,
	isActive: false,
};

// Initialize DOM cache
function initializeDOMCache() {
	DOM_CACHE.container = document.querySelector('.card.anomnaly-box');
	DOM_CACHE.carouselContainer = document.querySelector('.carousel-container');
	DOM_CACHE.itemsWrapper = DOM_CACHE.carouselContainer?.querySelector(
		'.carousel-items-wrapper',
	);
}

// Create carousel container if it doesn't exist
function createCarouselContainer() {
	if (DOM_CACHE.carouselContainer) return DOM_CACHE.carouselContainer;

	const carouselContainer = document.createElement('div');
	carouselContainer.className = 'carousel-container';

	// Create items wrapper
	const itemsWrapper = document.createElement('div');
	itemsWrapper.className = 'carousel-items-wrapper';
	carouselContainer.appendChild(itemsWrapper);

	// Create navigation buttons
	const prevButton = createNavigationButton(
		'nav-btn nav-left',
		left_icon_src,
		'Previous',
		-1,
	);
	const nextButton = createNavigationButton(
		'nav-btn nav-right',
		right_icon_src,
		'Next',
		1,
	);

	carouselContainer.appendChild(prevButton);
	carouselContainer.appendChild(nextButton);

	DOM_CACHE.container.appendChild(carouselContainer);

	// Update cache
	DOM_CACHE.carouselContainer = carouselContainer;
	DOM_CACHE.itemsWrapper = itemsWrapper;

	return carouselContainer;
}

// create navigation
function createNavigationButton(className, iconSrc, alt, direction) {
	const button = document.createElement('button');
	button.className = className;

	const icon = document.createElement('img');
	icon.src = iconSrc;
	icon.alt = alt;
	// icon.style.height = '50px';
	// icon.style.width = '50px';

	button.appendChild(icon);
	button.onclick = () => navigateCarousel(direction);

	return button;
}

// Generate form field HTML based on field configuration
function generateFieldHTML(
	fieldName,
	fieldConfig,
	boxIndex,
	defaultValue = '',
) {
	const fieldId = `${fieldName}-${boxIndex}`;
	const value = defaultValue || '';

	let inputHTML = '';

	switch (fieldConfig.type) {
		case 'select':
			const options = fieldConfig.options
				.map(
					(option) =>
						`<option value="${option}" ${option === defaultValue ? 'selected' : ''}>${option}</option>`,
				)
				.join('');
			inputHTML = `<select class="form-select form-select-sm" name="${fieldId}" id="${fieldId}">${options}</select>`;
			break;

		case 'textarea':
			inputHTML = `<textarea class="form-control form-control-sm" name="${fieldId}" id="${fieldId}" placeholder="${fieldConfig.placeholder || ''}" >${value}</textarea>`;
			break;

		case 'number':
			inputHTML = `<input type="number" class="form-control form-control-sm" name="${fieldId}" id="${fieldId}" value="${value}">`;
			break;

		default: // text
			const tsClass = fieldConfig.searchable ? 'ts' : '';
			inputHTML = `<input type="text" class="form-control form-control-sm ${tsClass}" id="${fieldId}" name="${fieldId}" value="${value}" placeholder="${fieldConfig.placeholder || ''}">`;
			break;
	}

	const colSize = fieldConfig.type === 'textarea' ? 'col-sm-12' : 'col-sm-2';
	const searchContainer = fieldConfig.searchable
		? `
        <div id="searchResults" class="small text-muted mt-1"></div>
        <div class="spinner-border spinner-border-sm text-primary mt-1" id="loader" style="display:none;" role="status"></div>
    `
		: '';

	return `
	<div class="${colSize} mb-2 ${fieldConfig.searchable ? 'timestamp-container' : ''}">
	<label class="col-form-label text-truncate w-100" style="font-size: 1.3rem; font-weight: 600; color: #6c757d; padding-bottom: 0;">${fieldConfig.label}</label>
	${inputHTML}
	${searchContainer}
</div>
    `;
}

const CATEGORY_CONFIGS = {
	furniture: {
		assets: {
			title: 'Asset Item',
			fields: {
				'Assets number': {
					label: 'Assets number',
					type: 'number',
					required: true,
				},
				'Timestamp on processed video': {
					label: 'Timestamp on processed video',
					type: 'text',
					searchable: true,
				},
				'Asset type': {
					label: 'Asset type',
					type: 'text',
					required: true,
				},
				Side: {
					label: 'Side',
					type: 'select',
					options: ['Right', 'Left', 'Avenue', 'Median', 'Overhead'],
				},
				Category: {
					label: 'Category',
					type: 'select',
					options: [
						'Cautionary Signs',
						'Mandatory Signs',
						'Informatory Signs',
						'Encroachment Signs',
						'Road Furniture',
					],
				},
				Latitude: { label: 'Latitude', type: 'text' },
				Longitude: { label: 'Longitude', type: 'text' },
				Distance: { label: 'Distance', type: 'text' },
				Length: {
					label: 'Length',
					type: 'text',
					placeholder: 'Enter Length',
				},
				'Average width': {
					label: 'Average width',
					type: 'text',
					placeholder: 'Enter Average Width',
				},
				Remarks: {
					label: 'Remarks',
					type: 'textarea',
					placeholder: 'Enter Remarks',
				},
				image: {
					label: 'Image',
					type: 'textarea',
					placeholder: 'Enter image link',
				},
			},
		},
		anomalies: {
			title: 'Anomaly Item',
			fields: {
				'Anomaly number': {
					label: 'Anomaly number',
					type: 'number',
					required: true,
				},
				'Timestamp on processed video': {
					label: 'Timestamp on processed video',
					type: 'text',
					searchable: true,
				},
				'Anomaly type': {
					label: 'Anomaly type',
					type: 'text',
					required: true,
				},
				Category: {
					label: 'Category',
					type: 'select',
					options: [
						'Cautionary Signs',
						'Mandatory Signs',
						'Informatory Signs',
						'Encroachment Signs',
						'Road Furniture',
						'Lane Markings',
					],
				},
				Latitude: { label: 'Latitude', type: 'text' },
				Longitude: { label: 'Longitude', type: 'text' },
				Distance: { label: 'Distance', type: 'text' },
				Length: { label: 'Length', type: 'text' },
				'Average width': { label: 'Average width', type: 'text' },
				Remarks: { label: 'Remarks', type: 'textarea' },
				image: {
					label: 'Image',
					type: 'textarea',
					placeholder: 'Enter image link',
				},
			},
		},
	},
	pavement: {
		anomalies: {
			title: 'Pavement Anomaly',
			fields: {
				'Anomaly number': {
					label: 'Anomaly number',
					type: 'number',
					required: true,
				},
				'Timestamp on processed video': {
					label: 'Timestamp on processed video',
					type: 'text',
					searchable: true,
				},
				'Anomaly type': {
					label: 'Anomaly type',
					type: 'text',
					required: true,
				},
				Category: {
					label: 'Category',
					type: 'select',
					options: [
						'Cautionary Signs',
						'Mandatory Signs',
						'Informatory Signs',
						'Encroachment Signs',
						'Road Furniture',
						'Lane Markings',
					],
				},
				'Frame no.': { label: 'Frame no.', type: 'text' },
				Latitude: { label: 'Latitude', type: 'text' },
				Longitude: { label: 'Longitude', type: 'text' },
				'Distance from start point in meters': {
					label: 'Distance from start point in meters',
					type: 'text',
				},
				'Length in meters': { label: 'Length in meters', type: 'text' },
				'Width in meters': { label: 'Width in meters', type: 'text' },
				image: {
					label: 'Image',
					type: 'textarea',
					placeholder: 'Enter image link',
				},
			},
		},
	},
};

const anomaly_box_sign_classes = {
	'Cautionary Signs': [
		'15_01_LEFT_HAND_CURVE',
		'15_01A_LEFT_SIDE_ROAD_ON_LEFT_CURVE',
		'15_01B_RIGHT_SIDE_ROAD_ON_LEFT_CURVE',
		'15_01C_CROSS_ROAD_ON_LEFT_CURVE',
		'15_01D_STAGGERED_INTERSECTION_ON_LEFT_CURVE',
		'15_02_RIGHT_HAND_CURVE',
		'15_02A_RIGHT_SIDE_ROAD_ON_RIGHT_CURVE',
		'15_02B_LEFT_SIDE_ROAD_ON_RIGHT_CURVE',
		'15_02C_CROSS_ROAD_ON_RIGHT_CURVE',
		'15_02D_STAGGERED_INTERSECTION_ON_RIGHT_CURVE',
		'15_03_RIGHT_HAIRPIN_BEND',
		'15_04_LEFT_HAIRPIN_BEND',
		'15_05_RIGHT_REVERSE_BEND',
		'15_06_LEFT_REVERSE_BEND',
		'15_07_SERIES_OF_BENDS',
		'15_08_270_DEGREE_LOOP',
		'15_09_SIDE_ROAD_RIGHT',
		'15_10_SIDE_ROAD_LEFT',
		'15_11_Y_INTERSECTION',
		'15_12_Y_INTERSECTION',
		'15_13_Y_INTERSECTION',
		'15_14_CROSS_ROADS',
		'15_15_ROUNDABOUT',
		'15_16_TRAFFIC_SIGNALS',
		'15_17_T_INTERSECTION',
		'15_18_T_INTERSECTION_MAJOR_ROAD_AHEAD',
		'15_19_MAJOR_ROAD_AHEAD',
		'15_20_STAGGERED_INTERSECTION',
		'15_21_MERGING_TRAFFIC',
		'15_22_MERGING_TRAFFIC_AHEAD_FROM_LEFT',
		'15_22A_MERGING_TRAFFIC_AHEAD_FROM_RIGHT',
		'15_23_NARROW_ROAD_AHEAD',
		'15_24_ROAD_WIDENS',
		'15_25_NARROW_BRIDGE_AHEAD',
		'15_26_STEEP_ASCENT',
		'15_27_STEEP_DESCENT',
		'15_28_REDUCED_CARRIAGEWAY_LEFT_LANE_REDUCED',
		'15_29_REDUCED_CARRIAGEWAY_RIGHT_LANE_REDUCED',
		'15_30_START_OF_DUAL_CARRIAGEWAY',
		'15_31_END_OF_DUAL_CARRIAGEWAY',
		'15_32_GAP_IN_MEDIAN',
		'15_33_PEDESTRIAN_CROSSING',
		'15_34_SCHOOL_AHEAD',
		'15_35_BUILT_UP_AREA',
		'15_36_TWO_WAY_OPERATION',
		'15_37_TWO_WAY_TRAFFIC_ON_CROSS_ROAD_AHEAD_WARNING',
		'15_38_LANE_CLOSED_TWO_LANE_CARRIAGEWAY',
		'15_39_LANE_CLOSED_THREE_LANE_CARRIAGEWAY',
		'15_40_LANE_CLOSED_FOUR_LANE_CARRIAGEWAY',
		'15_41_TRAFFIC_DIVERSION_ON_DUAL_CARRIAGEWAY',
		'15_42_PEOPLE_AT_WORK',
		'15_43_DANGER_WARNING',
		'15_44_DIFFERENTLY_ABLED_PERSONS_AHEAD',
		'15_45A_DEAF_PERSONS_AHEAD',
		'15_45B_BLIND_PERSONS_AHEAD',
		'15_46_CYCLE_CROSSING',
		'15_47_CYCLE_ROUTE_AHEAD',
		'15_48_DANGEROUS_DIP',
		'15_49_SPEED_BREAKER',
		'15_50_RUMBLE_STRIP',
		'15_51_ROUGH_ROAD',
		'15_52_SOFT_VERGES',
		'15_53_LOOSE_GRAVEL',
		'15_54_SLIPPERY_ROAD',
		'15_55_SLIPPERY_ROAD_BECAUSE_OF_ICE',
		'15_56_OPENING_OR_SWING_BRIDGE',
		'15_57_OVERHEAD_CABLES',
		'15_58_PLAYGROUND_AHEAD',
		'15_59_QUAY_SIDE_OR_RIVER_BANK',
		'15_60_BARRIER',
		'15_61_SUDDEN_SIDE_WINDS',
		'15_62_TUNNEL_AHEAD',
		'15_63_FERRY',
		'15_64_TRAMS_CROSSING',
		'15_65_FALLING_ROCKS',
		'15_66_CATTLE_CROSSING',
		'15_67_WILD_ANIMALS',
		'15_68_QUEUES_LIKELY_AHEAD',
		'15_69_LOW_FLYING_AIRCRAFT',
		'15_70_UNGUARDED_RAILWAY_CROSSING',
		'15_71_GUARDED_RAILWAY_CROSSING',
		'15_72_CRASH_PRONE_AREA_AHEAD',
		'15_73_U_TURN_AHEAD',
		'15_74_SINGLE_CHEVRON',
		'15_76_DOUBLE_CHEVRON',
		'15_77_TRIPLE_CHEVRON',
		'15_78_OBJECT_HAZARD_LEFT',
		'15_79_OBJECT_HAZARD_RIGHT',
		'15_80_TWO_WAY_OBJECT_HAZARD_MARKER',
	],
	'Mandatory Signs': [
		'14_01_STOP',
		'14_02_GIVE_WAY',
		'14_03_GIVE_WAY_TO_BUSES_EXITING_THE_BUS_BAY',
		'14_04_BULLOCK_CARTS_PROHIBITED',
		'14_05_BULLOCK_AND_HAND_CARTS_PROHIBITED',
		'14_06_HAND_CARTS_PROHIBITED',
		'14_07_TONGAS_PROHIBITED',
		'14_08_HORSE_RIDING_PROHIBITED',
		'14_09_AUTORICKSHAW_PROHIBITED',
		'14_10_BUSES_PROHIBITED',
		'14_11_CARS_PROHIBITED',
		'14_12_TRUCKS_PROHIBITED',
		'14_13_TRACTOR_PROHIBITED',
		'14_14_CONSTRUCTION_VEHICLE_PROHIBITED',
		'14_15_ARTICULATED_VEHICLES_PROHIBITED',
		'14_16_TWO_WHEELER_PROHIBITED',
		'14_17_CYCLES_PROHIBITED',
		'14_18_PEDESTRIAN_PROHIBITED',
		'14_19_HORN_PROHIBITED',
		'14_20_NO_ENTRY',
		'14_21_ONE_WAY',
		'14_22_LEFT_TURN_PROHIBITED',
		'14_23_RIGHT_TURN_PROHIBITED',
		'14_24_OVERTAKING_PROHIBITED',
		'14_25_U_TURN_PROHIBITED',
		'14_26_RIGHT_TURN_AND_U_TURN_PROHIBITED',
		'14_27_FREE_LEFT_TURN_PROHIBITED_AT_SIGNAL',
		'14_28_PRIORITY_TO_VEHICLES_FROM_OPPOSITE_DIRECTION',
		'14_29_NO_STANDING',
		'14_30_NO_STOPPING',
		'14_31_NO_PARKING',
		'14_32_PARKING_NOT_ALLOWED_ON_FOOTPATH',
		'14_33_PARKING_NOT_ALLOWED_ON_HALF_OF_FOOTPATH',
		'14_34_AXLE_LOAD_LIMIT',
		'14_35_HEIGHT_LIMIT',
		'14_36_LENGTH_LIMIT',
		'14_37_LOAD_LIMIT',
		'14_38_WIDTH_LIMIT',
		'14_39_MAXIMUM_SPEED_LIMIT',
		'14_40A_MAXIMUM_SPEED_LIMIT_VEHICLE_TYPE',
		'14_40B_MAXIMUM_SPEED_LIMIT_VEHICLE_TYPE',
		'14_41_STOP_FOR_POLICE_CHECK',
		'14_42_RESTRICTION_END_SIGN',
		'14_43_COMPULSORY_AHEAD',
		'14_44_COMPULSORY_AHEAD_OR_RIGHT_TURN',
		'14_45_COMPULSORY_AHEAD_OR_LEFT_TURN',
		'14_46_COMPULSORY_TURN_RIGHT',
		'14_47_COMPULSORY_TURN_LEFT',
		'14_47A_PRIORITY_TO_VEHICLES_FROM_RIGHT',
		'14_48_COMPULSORY_TURN_RIGHT_IN_ADVANCE_OF_JUNCTION',
		'14_49_COMPULSORY_TURN_LEFT_IN_ADVANCE_OF_JUNCTION',
		'14_50_COMPULSORY_KEEP_LEFT',
		'14_51_COMPULSORY_KEEP_RIGHT',
		'14_52_PASS_EITHER_SIDE',
		'14_53_MINIMUM_SPEED_LIMIT',
		'14_54_COMPULSORY_CYCLE_TRACK',
		'14_55_COMPULSORY_CYCLIST_AND_PEDESTRIAN_ROUTE',
		'14_56_PEDESTRIAN_ONLY',
		'14_57_COMPULSORY_SNOW_CHAIN',
		'14_58_BUS_WAY_BUSES_ONLY',
		'14_59_COMPULSORY_SOUND_HORN',
	],
	'Road Furniture': [
		'KM_STONE',
		'GUARD_POSTS',
		'SOLAR_BLINKER',
		'R_O_W_PILLAR',
		'SOS_FACILITY',
		'CCTV_CAMERA',
		'SPEED_DISPLAY_BOARD',
	],
	'Informatory Signs': [
		'16_01_STACK_TYPE_ADVANCE_DIRECTION_SIGN',
		'16_01A_ADVANCE_DIRECTION_SIGN',
		'16_02_MAP_TYPE_ADVANCE_DIRECTION_SIGN',
		'16_03_MAP_ADVANCE_DIRECTION_SIGN_ON_ROUNDABOUT',
		'16_04_FLAG_TYPE_DIRECTION_SIGN',
		'16_05_REASSURANCE_SIGN',
		'16_06_PLACE_IDENTIFICATION_SIGN',
		'16_07_TRUCK_LAY_BY_SIGN',
		'16_08_TOLL_BOOTH_AHEAD_SIGN',
		'16_09_WEIGH_BRIDGE_AHEAD_SIGN',
		'16_10_GANTRY_ADVANCE_DIRECTION_SIGN_GRADE_SEPARATED_JUNCTION',
		'16_11_GANTRY_ADVANCE_DIRECTION_SIGN_GRADE_JUNCTION',
		'16_12_ADVANCE_DIRECTION_SIGNS_FOR_AN_INTERCHANGE',
		'16_13_LANE_DEDICATED_GANTRY_SIGNS',
		'16_14A_SHOULDER_MOUNTED_SIGN_AHEAD_OF_GRADE_SEPARATED_JUNCTION',
		'16_14B_SHOULDER_MOUNTED_SIGN_AHEAD_OF_INTERCHANGE',
		'16_15_EXPRESSWAY_AHEAD_SIGN',
		'16_16_GANTRY_ADVANCE_DIRECTION_SIGN_FLYOVER_URBAN',
		'16_17_DEFINITION_SUPPLEMENTARY_PLATE',
		'16_18_TOURIST_DESTINATION_DIRECTION_WITHOUT_PHOTOGRAPH',
		'16_19_TOURIST_DESTINATION_DIRECTION_WITH_PHOTOGRAPH',
		'16_20_FINGER_DESTINATION_DIRECTION_FOR_PEDESTRIANS',
		'16_21_TOURIST_MAP_INFORMATION_SIGN',
		'16_22_BOUNDARY_SIGN_AT_ENTRANCE_TO_CITY_OR_PLACE',
		'16_23_BOUNDARY_SIGN_AT_ENTRANCE_TO_TOURIST_DESTINATION',
		'17_01_EATING_PLACE',
		'17_02_LIGHT_REFRESHMENT',
		'17_03_RESTING_PLACE',
		'17_04_FIRST_AID_POST',
		'17_05_TOILET',
		'17_06_FILLING_STATION',
		'17_07_HOSPITAL',
		'17_08_EMERGENCY_SOS_FACILITY',
		'17_09_U_TURN_AHEAD',
		'17_10_PEDESTRIAN_SUBWAY',
		'17_11_FOOT_OVER_BRIDGE',
		'17_12_CHAIR_LIFT',
		'17_13_POLICE_STATION',
		'17_14_REPAIR_FACILITY',
		'17_15_RAILWAY_METRO_MONORAIL_STATION',
		'17_16_PUBLIC_BIKE_SHARING_STAND',
		'17_17_CYCLE_RICKSHAW_STAND',
		'17_18_TAXI_STAND',
		'17_19_AUTORICKSHAW_STAND',
		'17_20_SHARE_TAXI_OR_AUTO_STAND',
		'17_21_HOME_ZONE',
		'17_22_CAMP_SITE',
		'17_23_AIRPORT',
		'17_24_GOLF_COURSE',
		'17_25_NATIONAL_HERITAGE',
		'17_26_NO_THROUGH_ROAD',
		'17_27_NO_THROUGH_SIDE_ROAD',
		'17_28_TOLL_ROAD_AHEAD',
		'17_29_GUIDE_SIGN_ON_ETC_LANE',
		'17_30_COUNTRY_BORDER',
		'17_31_ENTRY_RAMP_FOR_EXPRESSWAY',
		'17_32_EXIT_RAMP_FOR_EXPRESSWAY',
		'17_33_EXPRESSWAY_SYMBOL',
		'17_34_END_OF_EXPRESSWAY',
		'17_35_BUS_STOP',
		'17_36_BUS_LANE',
		'17_37_CONTRA_FLOW_BUS_LANE',
		'17_38_CYCLE_LANE',
		'17_39_CONTRA_FLOW_CYCLE_LANE',
		'17_40_HOLIDAY_CHALETS',
		'17_41_EMERGENCY_EXIT',
		'17_42_EMERGENCY_EXIT',
		'17_43_EMERGENCY_HELPLINE_NUMBER',
		'17_44_EMERGENCY_LAYBY',
		'17_45_FIRE_EXTINGUISHER',
		'17_46_REST_AND_SERVICE_AREA_SIGN',
		'17_47_PEDESTRIAN_CROSSING_INFORMATION_SIGN',
		'17_48_SPEED_BREAKER_INFORMATION_SIGN',
		'17_49_ELECTRIC_VEHICLE_CHARGING_STATION',
		'18_01_PARKING',
		'18_02_AUTORICKSHAW_PARKING',
		'18_03_CYCLE_PARKING',
		'18_04_CYCLE_RICKSHAW_PARKING',
		'18_05_SCOOTER_AND_MOTORCYCLE_PARKING',
		'18_06_TAXI_PARKING',
		'18_06A_CAR_PARKING',
		'18_07_PARK_AND_RIDE_BY_METRO',
		'18_08_PARK_AND_RIDE_BY_BUS',
		'18_09_PICKUP_AND_DROP_POINT',
		'18_10_PARKING_RESTRICTION_SIGN_FOR_TRAFFIC_MANAGEMENT',
		'18_11_FLOOD_GAUGE',
		'19_01_INTERNATIONAL_SYMBOL_OF_ACCESSIBILITY',
		'19_02_PARKING_INFORMATION',
		'19_03_PARKING_AREAS',
		'19_04_RAMPED_ENTRANCE_TO_SUBWAY_OR_OVERBRIDGE',
		'19_05_TOILET_FACILITIES',
		'19_06_WAY_FINDING',
		'20_01_RED_LIGHT_VIOLATION_PENALTY',
		'20_02_STOP_SIGN_VIOLATION_PENALTY',
		'20_03_SPEED_CAMERA',
		'20_04_VEHICLE_CATEGORY_AND_SPEED_WISE_LANE_DEDICATION',
		'20_04A_VEHICLE_CATEGORY_WISE_LANE_DEDICATION_SHOULDER',
		'20_05_TOW_AWAY_ZONE_SIGN',
		'20_06_LANE_PRIORITY_SIGN_FOR_EMERGENCY_VEHICLES',
		'22_01_STATE_HIGHWAY_ROUTE_MARK_SIGN',
		'22_02_NATIONAL_HIGHWAY_ROUTE_MARKER_SIGN',
		'22_03_ASIAN_HIGHWAY_ROUTE_MARKER_SIGN',
		'22_04_EXPRESSWAY_ROUTE_MARKER_SIGN',
		'24_02_LANDMARK_IDENTIFICATION_SIGN',
		'24_01_FINGER_TYPE_SIGNAGE_FOR_PEDESTRIAN_PREDOMINANT_STREET',
		'24_03_STREET_NAME_BOARD',
		'25_01_TOLL_PLAZA_AHEAD_OVERHEAD_CANTILEVER_SIGN',
		'25_02_TOLL_LANE_INFORMATION_OVERHEAD_SIGN',
		'25_03_TOLL_PLAZA_CANOPY_SIGN',
		'INFORMATORY_SIGNS',
		'NON_STANDARD_INFOMATORY_SIGNS',
	],
	'Encroachment Signs': ['ADVERTISEMENT_ENCHROACHMENT_SIGNS'],
};

const categorySelect = document.getElementById('categorySelect');
const anomalyTypeSelect = document.getElementById('anomalyTypeSelect');

let isEditing = false;
let isEditingCanvas = false;
let startX,
	startY,
	isDrawing = false;
let boundingBoxes = [];
let canvasWidth = window.innerWidth * 0.6;
let canvasHeight = window.innerHeight * 0.6;
const image = new Image();

// download Canva Image
function downloadCanvasImage(img_src) {
	const imageData = canvas.toDataURL('image/png');
	const originalFileName = img_src.substring(img_src.lastIndexOf('/') + 1);
	const link = document.createElement('a');
	link.href = imageData;
	link.download = originalFileName || 'default_image_name.png';
	console.log('Original File Name:', originalFileName);
	document.body.appendChild(link);
	link.click();
	document.body.removeChild(link);
}

// Add event listener to the button
document.getElementById('downloadImageButton').addEventListener('click', () => {
	downloadCanvasImage(image.src);
});

// image load
image.onload = () => {
	resizeCanvas(canvasWidth, canvasHeight);
	ctx.drawImage(image, 0, 0, canvasWidth, canvasHeight);
};

// Resize canvas based on the selected resolution
function resizeCanvas(width, height) {
	canvas.width = width;
	canvas.height = height;
	canvasWidth = width;
	canvasHeight = height;

	redrawBoundingBoxes();

	// ctx.clearRect(0, 0, canvasWidth, canvasHeight);
	// ctx.drawImage(image, 0, 0, canvasWidth, canvasHeight);
	// boundingBoxes.forEach(
	// 	({ x, y, width, height, label, color, trackid, trackidColor }) => {
	// 		drawBoundingBox(
	// 			x,
	// 			y,
	// 			width,
	// 			height,
	// 			label,
	// 			color,
	// 			trackid,
	// 			trackidColor,
	// 		);
	// 	},
	// );
}

// Handle resolution change
resolutionSelect.addEventListener('change', () => {
	const [width, height] = resolutionSelect.value.split('x').map(Number);
	resizeCanvas(width, height);
});

editButton.addEventListener('click', () => {
	isEditing = !isEditing;
	isEditingCanvas = !isEditingCanvas;
	editButton.textContent = isEditingCanvas ? 'Done' : 'Edit';

	if (isEditingCanvas) {
		console.log('Editing mode enabled.');
		// Reset editing session when starting new editing mode
		EDITING_SESSION.timestamp = null;
		EDITING_SESSION.locationData = null;
		EDITING_SESSION.isActive = true;
	} else {
		console.log('Editing mode disabled. Running collectAndSendAnomalies.');
		// Clear editing session when finishing
		EDITING_SESSION.isActive = false;
		EDITING_SESSION.timestamp = null;
		EDITING_SESSION.locationData = null;

		collectAndSendAnomalies();
		send_data_to_backend();

		const selectedCategory =
			document.getElementById('categorySelect').value;
		const selectedLabel = document.getElementById('labelSelect').value;
		const assets = anomalyData[selectedCategory]?.assets || {};
		const isFromAssets = assets.hasOwnProperty(selectedLabel);
	}
});

// Start drawing bounding box
canvas.addEventListener('mousedown', (e) => {
	if (!isEditing) return;
	const rect = canvas.getBoundingClientRect();
	startX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
	startY = ((e.clientY - rect.top) / rect.height) * canvasHeight;
	isDrawing = true;
});

// Draw rectangle while dragging
// canvas.addEventListener('mousemove', (e) => {
// 	if (!isDrawing) return;
// 	const rect = canvas.getBoundingClientRect();
// 	const currentX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
// 	const currentY = ((e.clientY - rect.top) / rect.height) * canvasHeight;

// 	ctx.clearRect(0, 0, canvasWidth, canvasHeight);
// 	ctx.drawImage(image, 0, 0, canvasWidth, canvasHeight);
// 	boundingBoxes.forEach(
// 		({ x, y, width, height, label, color, trackid, trackidColor }) => {
// 			drawBoundingBox(
// 				x,
// 				y,
// 				width,
// 				height,
// 				label,
// 				color,
// 				trackid,
// 				trackidColor,
// 			);
// 		},
// 	);

// 	ctx.strokeStyle = 'red';
// 	ctx.lineWidth = 2;
// 	ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
// });

// updateLabelOptions
function updateLabelOptions(category) {
	const labelSelect = document.getElementById('labelSelect');
	labelSelect.innerHTML = '';
	const assets = anomalyData[category]?.assets || {};
	const anomalies = anomalyData[category]?.anomalies || {};
	const labels = { ...assets, ...anomalies };

	for (const label in labels) {
		const option = document.createElement('option');
		option.value = label;
		option.textContent = label;
		labelSelect.appendChild(option);
	}
}

// Event listener for category select change
document.getElementById('categorySelect').addEventListener('change', (e) => {
	const selectedCategory = e.target.value;
	updateLabelOptions(selectedCategory); // Update label options based on selected category
});

// Initialize the label select options on page load based on default selected category
window.onload = () => {
	const defaultCategory = document.getElementById('categorySelect').value;
	updateLabelOptions(defaultCategory);
};

// Function to redraw all bounding boxes
function redrawBoundingBoxes() {
	ctx.clearRect(0, 0, canvasWidth, canvasHeight); // Clear the canvas
	ctx.drawImage(image, 0, 0, canvasWidth, canvasHeight); // Redraw the image

	// Redraw all bounding boxes
	boundingBoxes.forEach(
		({ x, y, width, height, label, color, trackid, trackidColor }) => {
			drawBoundingBox(
				x,
				y,
				width,
				height,
				label,
				color,
				trackid,
				trackidColor,
			);
		},
	);
}

// Update the drawBoundingBox function
function drawBoundingBox(
	x,
	y,
	width,
	height,
	label,
	color,
	trackid,
	trackidColor,
) {
	ctx.strokeStyle = color; // Set the color for the bounding box
	ctx.lineWidth = 2;
	ctx.strokeRect(x, y, width, height);

	// Add label text
	ctx.fillStyle = color; // Use the same color for the label text
	ctx.font = '12px Arial';
	ctx.fillText(label, x, y - 10); // Adjust text position slightly inside the box

	// Add trackid text
	if (trackid) {
		// Draw central green ring
		const centerX = x + width / 2;
		const centerY = y + height / 2;

		ctx.beginPath();
		ctx.arc(centerX, centerY, trackIdDotRadius, 0, 2 * Math.PI);
		ctx.strokeStyle = '#0dff00'; // Green color for the ring
		ctx.lineWidth = 1;
		ctx.stroke();
		ctx.closePath();

		// Add trackid text above the ring
		ctx.fillStyle = trackidColor; // Use the specific color for trackid text (Cyan/Yellow)
		ctx.font = '14px Arial';
		ctx.textAlign = 'center';
		ctx.textBaseline = 'bottom';

		// Position text above the ring with a small margin
		ctx.fillText(trackid, centerX, centerY - trackIdDotRadius - 2);

		// Reset text alignment for other drawings
		ctx.textAlign = 'start';
		ctx.textBaseline = 'alphabetic';
	}
}

// Main function to create anomaly fields
function createAnomalyFields(
	boxIndex,
	selectedLabel,
	img_url,
	selectedCategory,
) {
	if (!DOM_CACHE.container) {
		initializeDOMCache();
	}
	createCarouselContainer();

	const subcategory = determineSubcategory(selectedCategory, selectedLabel);
	const config = CATEGORY_CONFIGS[selectedCategory]?.[subcategory];

	if (!config) {
		console.error(
			`Config not found for: category='${selectedCategory}', subcategory='${subcategory}'`,
		);
		return;
	}

	const anomalyDiv = document.createElement('div');
	anomalyDiv.className = 'carousel-item';
	anomalyDiv.id = `anomaly-${boxIndex}`;
	anomalyDiv.dataset.category = selectedCategory;
	anomalyDiv.dataset.subcategory = subcategory;

	const fieldsHTML = Object.entries(config.fields)
		.map(([fieldName, fieldConfig]) => {
			let defaultValue = '';
			switch (fieldName) {
				/* Update the defaultValue cases as follows */

				case 'Assets number':
					// Count how many 'Assets number' inputs already exist in the sidebar
					let currentSidebarAssets = document.querySelectorAll(
						'input[name^="Assets number-"]',
					).length;
					let sequentialAssetsNum =
						(window.totalExistingAssets || 0) +
						currentSidebarAssets +
						1;
					defaultValue =
						window.currentFrameNumber + '.' + sequentialAssetsNum;
					break;

				case 'Anomaly number':
					// Count how many 'Anomaly number' inputs already exist in the sidebar
					let currentSidebarAnomalies = document.querySelectorAll(
						'input[name^="Anomaly number-"]',
					).length;
					let sequentialAnomaliesNum =
						(window.totalExistingAnomalies || 0) +
						currentSidebarAnomalies +
						1;
					defaultValue =
						window.currentFrameNumber +
						'.' +
						sequentialAnomaliesNum;
					break;

				case 'Asset type':
				case 'Anomaly type':
					defaultValue = selectedLabel;
					break;
				case 'image':
					defaultValue = img_url;
					break;
				case 'Timestamp on processed video':
					// Use stored timestamp if available
					defaultValue = EDITING_SESSION.timestamp || '';
					break;
				case 'Latitude':
					defaultValue = EDITING_SESSION.locationData?.lat || '';
					break;
				case 'Longitude':
					defaultValue = EDITING_SESSION.locationData?.lng || '';
					break;
				case 'Distance':
				case 'Distance from start point in meters':
					defaultValue =
						EDITING_SESSION.locationData?.distanceInMeters || '';
					break;
				case 'Category':
					// Auto-fill category based on selectedLabel
					const cleanLabel = selectedLabel.replace(
						/^(DAMAGED_|FADED_)/,
						'',
					);
					for (const [category, labels] of Object.entries(
						anomaly_box_sign_classes,
					)) {
						if (
							labels.includes(selectedLabel) ||
							labels.includes(cleanLabel)
						) {
							defaultValue = category;
							break;
						}
					}
					break;
			}
			return generateFieldHTML(
				fieldName,
				fieldConfig,
				boxIndex,
				defaultValue,
			);
		})
		.join('');

	anomalyDiv.innerHTML = `
	<div class="row anomaly_form m-0">
	<div class="col-12 inside_anomaly">
		<h3>${config.title} ${boxIndex + 1}</h3>
	</div>
	${fieldsHTML}
</div>
    `;

	if (DOM_CACHE.itemsWrapper.children.length === 0) {
		anomalyDiv.classList.add('active');
	}

	console.log('Creating anomaly div with stored data:', EDITING_SESSION);

	DOM_CACHE.itemsWrapper.appendChild(anomalyDiv);

	// Only attach event listeners if this is the first box (to set the session data)
	if (boxIndex === 0 || !EDITING_SESSION.timestamp) {
		attachEventListeners(anomalyDiv, boxIndex, config);
	}
}

// Also double-check your determineSubcategory function
function determineSubcategory(selectedCategory, selectedLabel) {
	// Check assets first
	if (
		CATEGORY_CONFIGS[selectedCategory]?.assets?.hasOwnProperty(
			selectedLabel,
		) ||
		anomalyData[selectedCategory]?.assets?.hasOwnProperty(selectedLabel)
	) {
		return 'assets';
	}
	// Check anomalies
	if (
		CATEGORY_CONFIGS[selectedCategory]?.anomalies?.hasOwnProperty(
			selectedLabel,
		) ||
		anomalyData[selectedCategory]?.anomalies?.hasOwnProperty(selectedLabel)
	) {
		return 'anomalies';
	}
	// Default or fallback
	return 'anomalies';
}

function navigateCarousel(direction) {
	const items = document.querySelectorAll('.carousel-item');

	if (items.length === 0) return;

	// Remove `active` class from the current item
	items[currentCarouselIndex].classList.remove('active');

	// Update index
	currentCarouselIndex =
		(currentCarouselIndex + direction + items.length) % items.length;

	// Add `active` class to the new item
	items[currentCarouselIndex].classList.add('active');
}

// Event listener for canvas mouseup event
canvas.addEventListener('mouseup', (e) => {
	if (!isDrawing) return;

	const rect = canvas.getBoundingClientRect();
	const endX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
	const endY = ((e.clientY - rect.top) / rect.height) * canvasHeight;
	isDrawing = false;

	const width = endX - startX;
	const height = endY - startY;

	const labelSelect = document.getElementById('labelSelect');
	const categorySelect = document.getElementById('categorySelect');
	const selectedLabel = labelSelect.value;
	const selectedCategory = categorySelect.value;

	const surveyId = document.getElementById('surveyId').value;
	const roadId = document.getElementById('roadId').value;

	console.log(surveyId, roadId, 'loading ....');

	const imageName = image.src.split('/').pop();
	console.log('Image name:', imageName);

	const assets = anomalyData[selectedCategory]?.assets || {};
	const anomalies = anomalyData[selectedCategory]?.anomalies || {};

	const isFromAssets = assets.hasOwnProperty(selectedLabel);
	const isFromAnomalies = anomalies.hasOwnProperty(selectedLabel);

	const colorArray = isFromAssets
		? assets[selectedLabel]
		: anomalies[selectedLabel];

	console.log('Anomaly data', {
		selectedCategory,
		selectedLabel,
		anomalyData,
		isFromAssets,
		isFromAnomalies,
		colorArray,
	});

	if (!colorArray) {
		console.warn('No color found for selected label:', selectedLabel);
		return;
	}

	let basePath = `https://raiotransection.s3.ap-south-1.amazonaws.com/output/${subdomain}/${selectedCategory}/`;
	basePath += isFromAssets ? 'assets/frames' : 'anomalies/frames';

	const imgUrl =
		`${basePath}/survey_${surveyId}/road_${roadId}/${imageName}`.replace(
			/%20/g,
			'_',
		);
	console.log('Image URL:', imgUrl);

	const rgbColor = `rgb(${colorArray[0]}, ${colorArray[1]}, ${colorArray[2]})`;
	console.log('RGB Color:', rgbColor);

	// Generate random trackid (Format: Id_X_YY)
	const singleDigit = Math.floor(Math.random() * 10);
	const twoDigit = Math.floor(Math.random() * 100)
		.toString()
		.padStart(2, '0');
	const randomTrackId = `Id_${singleDigit}_${twoDigit}`;

	// Determine trackid color based on category
	let trackidColor = 'cyan'; // Default for furniture
	if (selectedCategory === 'pavement') {
		trackidColor = 'yellow';
	}

	boundingBoxes.push({
		x: startX,
		y: startY,
		width,
		height,
		label: selectedLabel,
		color: rgbColor,
		trackid: randomTrackId,
		trackidColor: trackidColor,
	});
	// enable the undo button after drawing at least one bounding box
	updateUndoButtonState();
	redrawBoundingBoxes();

	console.log('Selected Items:', {
		selectedLabel,
		selectedCategory,
		imgUrl,
	});

	uploadImage(isFromAssets);

	createAnomalyFields(
		boundingBoxes.length - 1,
		selectedLabel,
		imgUrl,
		selectedCategory,
	);
});

// Event listener for canvas mousemove to dynamically draw while dragging
canvas.addEventListener('mousemove', (e) => {
	if (!isDrawing) return;
	const rect = canvas.getBoundingClientRect();
	const currentX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
	const currentY = ((e.clientY - rect.top) / rect.height) * canvasHeight;

	// Redraw the image and existing bounding boxes
	redrawBoundingBoxes();

	// Draw the currently dragged bounding box
	ctx.strokeStyle = 'red';
	ctx.lineWidth = 2;
	ctx.strokeRect(startX, startY, currentX - startX, currentY - startY);
});
function debounce(fn, delay = 300) {
	let timer;
	return function (...args) {
		clearTimeout(timer);
		timer = setTimeout(() => fn.apply(this, args), delay);
	};
}

function attachEventListeners(anomalyDiv, boxIndex, config) {
	console.log('Attaching event listeners for box:', boxIndex);

	Object.entries(config.fields).forEach(([fieldName, fieldConfig]) => {
		if (fieldConfig.searchable) {
			// Construct the name attribute exactly as it is in generateFieldHTML
			const fieldId = `${fieldName}-${boxIndex}`;

			// Use a querySelector that finds the input by its 'name' attribute
			const input = anomalyDiv.querySelector(`[name="${fieldId}"]`);

			if (input) {
				console.log('Found input for', fieldName, 'adding listener.');
				input.addEventListener(
					'input',
					debounce((e) => {
						const data = { timestamp: e.target.value };
						addSearchFunctionalityts(data, boxIndex);
					}, 300),
				);
			} else {
				console.warn(
					`Input element not found for field: ${fieldName}, with name: ${fieldId}`,
				);
			}
		}
	});
}

function addSearchFunctionalityts(data, boxIndex) {
	const searchBox = data.timestamp;
	const container = document.getElementById('searchResults');
	const loader = document.getElementById('loader');

	if (loader) loader.style.display = 'inline-block';
	if (container) container.innerHTML = '';

	const searchKey = searchBox.trim();
	if (searchKey === '') {
		if (loader) loader.style.display = 'none';
		if (container) container.innerHTML = '<div>No results found</div>';
		return;
	}

	let found = false;

	const match = gpx_data[searchKey];
	if (match) {
		found = true;
		// Store in editing session
		EDITING_SESSION.timestamp = searchKey;
		EDITING_SESSION.locationData = {
			lat: match.lat,
			lng: match.lng,
			distanceInMeters: match.distanceInMeters,
		};
		console.log('Stored editing session data:', EDITING_SESSION);
		if (container) {
			// Display found data confirmation
			container.innerHTML = `<div><strong>${searchKey}</strong> - Data Found!</div>`;
		}

		updateFieldValue(boxIndex, 'Latitude', match.lat);
		updateFieldValue(boxIndex, 'Longitude', match.lng);
		updateFieldValue(boxIndex, 'Distance', match.distanceInMeters);
		updateFieldValue(
			boxIndex,
			'Distance from start point in meters',
			match.distanceInMeters,
		);
	}

	if (!found && container) {
		container.innerHTML =
			'<div>No matching key found in the GPX data.</div>';
	}
	// Reduced delay for better responsiveness
	// Search through gpx_data for the matching timestamp
	// for (const [key, value] of Object.entries(gpx_data)) {
	// 	if (key === searchKey) {
	// 		found = true;
	// 		// Store in editing session
	// 		EDITING_SESSION.timestamp = searchKey;
	// 		EDITING_SESSION.locationData = {
	// 			lat: value.lat,
	// 			lng: value.lng,
	// 			distanceInMeters: value.distanceInMeters,
	// 		};
	// 		console.log('Stored editing session data:', EDITING_SESSION);
	// 		if (container) {
	// 			// Display found data confirmation
	// 			container.innerHTML = `<div><strong>${key}</strong> - Data Found!</div>`;
	// 		}

	// 		updateFieldValue(boxIndex, 'Latitude', value.lat);
	// 		updateFieldValue(boxIndex, 'Longitude', value.lng);
	// 		updateFieldValue(boxIndex, 'Distance', value.distanceInMeters);
	// 		updateFieldValue(
	// 			boxIndex,
	// 			'Distance from start point in meters',
	// 			value.distanceInMeters,
	// 		);

	// 		break;
	// 	}
	// }
}

// UPLOAD FIELD VALUE
function updateFieldValue(boxIndex, fieldName, value) {
	const anomalyDiv = document.getElementById(`anomaly-${boxIndex}`);
	if (!anomalyDiv) {
		console.warn(`Could not find anomaly container for index: ${boxIndex}`);
		return;
	}
	const input = anomalyDiv.querySelector(`[name="${fieldName}-${boxIndex}"]`);

	if (input) {
		input.value = value;
		input.style.backgroundColor = 'lightgreen'; // Visual feedback
	} else {
		console.warn(
			`Could not find field "${fieldName}-${boxIndex}" in anomaly form ${boxIndex}`,
		);
	}
}
function getCSRFToken() {
	let cookieValue = null;
	const name = 'csrftoken';

	if (document.cookie && document.cookie !== '') {
		const cookies = document.cookie.split(';');

		for (let i = 0; i < cookies.length; i++) {
			const cookie = cookies[i].trim();

			if (cookie.startsWith(name + '=')) {
				cookieValue = decodeURIComponent(
					cookie.substring(name.length + 1),
				);
				break;
			}
		}
	}
	return cookieValue;
}
// Function to undo the last bounding box
function undoLastBoundingBox() {
	if (boundingBoxes.length === 0) {
		console.log('No bounding boxes to undo');
		return;
	}

	// Remove the last bounding box from the array
	const removedBox = boundingBoxes.pop();
	console.log('Removed bounding box:', removedBox);

	// Remove the corresponding anomaly form from the DOM
	const removedIndex = boundingBoxes.length; // Index of the removed box
	const anomalyDiv = document.getElementById(`anomaly-${removedIndex}`);
	if (anomalyDiv) {
		anomalyDiv.remove();
		console.log(`Removed anomaly-${removedIndex} from DOM`);
	}

	// Update carousel index if needed
	const items = document.querySelectorAll('.carousel-item');
	if (items.length > 0) {
		// Remove active class from current item
		items.forEach((item) => item.classList.remove('active'));

		// Set carousel index to the last valid item or 0
		currentCarouselIndex = Math.min(currentCarouselIndex, items.length - 1);
		if (items[currentCarouselIndex]) {
			items[currentCarouselIndex].classList.add('active');
		}
	} else {
		currentCarouselIndex = 0;
	}

	// Redraw the canvas without the removed bounding box
	redrawBoundingBoxes();

	// Update undo button state
	updateUndoButtonState();

	console.log('Bounding boxes remaining:', boundingBoxes.length);
}

// Function to update the undo button state
function updateUndoButtonState() {
	if (undoButton) {
		if (boundingBoxes.length > 0) {
			undoButton.disabled = false;
		} else {
			undoButton.disabled = true;
		}
	}
}

// Event listener for undo button
if (undoButton) {
	undoButton.addEventListener('click', undoLastBoundingBox);
}

function getCleanCanvasBlob(callback) {
	// 1. Clear everything
	ctx.clearRect(0, 0, canvasWidth, canvasHeight);

	// 2. Draw ONLY the original image
	ctx.drawImage(image, 0, 0, canvasWidth, canvasHeight);

	// 3. Convert to blob (NO bounding boxes)
	canvas.toBlob((blob) => {
		if (!blob) {
			console.error('Failed to create blob');
			return;
		}

		// 4. Restore bounding boxes visually
		redrawBoundingBoxes();

		// 5. Return clean blob
		callback(blob);
	}, 'image/png');
}

function send_data_to_backend() {
	getCleanCanvasBlob((blob) => {
		const formData = new FormData();

		formData.append('image', blob, 'frame.png');
		formData.append('survey_id', document.getElementById('surveyId').value);
		formData.append('road_id', document.getElementById('roadId').value);

		fetch('/upload-image/', {
			method: 'POST',
			body: formData,
			headers: {
				'X-CSRFToken': getCSRFToken(),
			},
		})
			.then((res) => res.json())
			.then((data) => {
				console.log('Upload success:', data);
			})
			.catch((err) => {
				console.error('Upload error:', err);
			});
	});
}
