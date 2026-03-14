canvas.addEventListener('mouseup', (e) => {
    if (!isDrawing) {
        // Check if the click is on any "X" button
        const rect = canvas.getBoundingClientRect();
        const clickX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
        const clickY = ((e.clientY - rect.top) / rect.height) * canvasHeight;

        // Check if the click is on any bounding box's "X" button
        for (let i = 0; i < boundingBoxes.length; i++) {
            const { crossX, crossY, crossSize } = boundingBoxes[i];
            if (
                clickX >= crossX &&
                clickX <= crossX + crossSize &&
                clickY >= crossY &&
                clickY <= crossY + crossSize
            ) {
                boundingBoxes.splice(i, 1); // Remove this bounding box
                redrawBoundingBoxes(); // Refresh the canvas
                return; // Stop checking further
            }
        }
        return; // Exit since we are not drawing
    }

    const rect = canvas.getBoundingClientRect();
    const endX = ((e.clientX - rect.left) / rect.width) * canvasWidth;
    const endY = ((e.clientY - rect.top) / rect.height) * canvasHeight;
    isDrawing = false;

    const width = endX - startX;
    const height = endY - startY;

    const labelSelect = document.getElementById('labelSelect');
    const categorySelect = document.getElementById('categorySelect');
    const selectedLabel = labelSelect.value; // Get the selected label
    const selectedCategory = categorySelect.value; // Get the selected category

    const surveyId = document.getElementById('surveyId').value;
    const roadId = document.getElementById('roadId').value;

    console.log(surveyId, roadId, "loading ....");
    image_name = image.src.split('/').pop();
    console.log(image_name);

    img_url = `https://raiotransection.s3.ap-south-1.amazonaws.com/${selectedCategory}/output/frames/survey_${surveyId}/road_${roadId}/${image_name}`;
    img_url = img_url.replace(/%20/g, '_');

    console.log(img_url);

    if (selectedLabel) {
        // Get the color for the selected label
        const color = anomalyData[selectedCategory][selectedLabel]
            .replace(/[()]/g, '') // Remove parentheses
            .split(',') // Split into RGB values
            .map(value => parseInt(value.trim())); // Convert to integers

        const rgbColor = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;

        // Add the bounding box to the list
        boundingBoxes.push({
            x: startX,
            y: startY,
            width,
            height,
            label: selectedLabel,
            color: rgbColor,
            crossX: startX + width - 15, // Store cross position
            crossY: startY,
            crossSize: 15
        });

        // Redraw all bounding boxes
        redrawBoundingBoxes();
        console.log(selectedLabel, selectedCategory, "select items ");

        // Create anomalies fields
        createAnomalyFields(boundingBoxes.length - 1, selectedLabel, img_url);
    }
});
