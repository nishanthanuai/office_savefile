// Dropdown for folder selection
const dropdown = document.getElementById("folderSelect");
const uploadForm = document.getElementById("uploadForm");
const fileInput = document.getElementById("fileInput");
const uploadStatus = document.getElementById("uploadStatus");
const fileList = document.getElementById("fileList");
const deleteButton = document.getElementById("deleteButton");
const deleteStatus = document.getElementById("deleteStatus");
const runScriptButton = document.getElementById("runScriptButton");
const scriptStatus = document.getElementById("scriptStatus");
const uploadFormArea = document.querySelector(".upload_Form_area");
const downloadExcelBtn = document.getElementById("download-excel-btn");
const roadIdDiv = document.getElementById("road-id");
const excelInputDiv = document.getElementById("excel-name");
const roadIdInput = document.getElementById("road_id");
const nameInput = document.getElementById("file_name");

// Event listener for folder selection dropdown
dropdown.addEventListener("change", function (event) {
  const selectedValue = event.target.value;
  console.log("Selected Value:", selectedValue);

  if (selectedValue) {
    // Fetch files for the selected folder
    fetch(`/excelmerge/get-files/${selectedValue}/`)
      .then((response) => {
        console.log(response)
        if (!response.ok) {
          throw new Error("Folder not found");
        }
        return response.json();
      })
      .then((data) => {
        // Clear the file list
        if (data.files.length !== 0) {
          fileList.innerHTML = "";
        } else {
          fileList.innerHTML = "No files in the folder";
        }

        if (data.error) {
          fileList.innerHTML = `<li>${data.error}</li>`;
          return;
        }

        // Populate file list
        data.files.forEach((file) => {
          const listItem = document.createElement("li");
          listItem.textContent = file;
          fileList.appendChild(listItem);
        });
      })
      .catch((error) => {
        fileList.innerHTML = `<li>Error: ${error.message}</li>`;
      });
  } else {
    fileList.innerHTML = "<li>No folder selected</li>";
  }

  // Clear upload and delete statuses when folder changes
  uploadStatus.innerHTML = "";
  deleteStatus.innerHTML = "";
  scriptStatus.innerHTML = ""
});


fileInput.addEventListener("change", () => {
  uploadStatus.innerHTML = "";
  scriptStatus.innerHTML = ""
});

// Upload form submission
uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();

  const selectedFolder = dropdown.value;

  if (!selectedFolder) {
    alert("Please select a folder from the dropdown.");
    return;
  }

  if (fileInput.files.length === 0) {
    alert("Please select a file to upload.");
    return;
  }

  const formData = new FormData();
  Array.from(fileInput.files).forEach((file) => {
    formData.append("files[]", file);
  });

  try {
    // Upload files
    const uploadResponse = await fetch(`/excelmerge/upload-file/${selectedFolder}/`, {
      method: "POST",
      body: formData,
    });

    const uploadData = await uploadResponse.json();
    if (uploadData.error) {
      uploadStatus.innerHTML = `<li class="error">Error: ${uploadData.error}</li>`;
      return;
    }

    uploadStatus.innerHTML = `<li class="success">${uploadData.message}</li>`;
    fileInput.value = ""

    // Fetch updated file list
    const listResponse = await fetch(`/excelmerge/get-files/${selectedFolder}/?t=${Date.now()}`);
    if (!listResponse.ok) throw new Error("Failed to fetch updated file list");

    const listData = await listResponse.json();
    fileList.innerHTML = ""; // Clear previous list

    if (listData.error) {
      fileList.innerHTML = `<li>${listData.error}</li>`;
      return;
    }

    listData.files.forEach((file) => {
      const listItem = document.createElement("li");
      listItem.textContent = file;
      fileList.appendChild(listItem);
    });
  } catch (error) {
    uploadStatus.innerHTML = `<li class="error">Error: ${error.message}</li>`;
  }
});

// Delete all files in the selected folder
deleteButton.addEventListener("click", () => {
  const selectedFolder = dropdown.value;
  uploadStatus.innerHTML = ""

  if (!selectedFolder) {
    alert("Please select a folder from the dropdown.");
    return;
  }

  const confirmation = confirm(
    `Are you sure you want to delete all files in the folder '${selectedFolder}'?`
  );
  if (!confirmation) return;

  fetch(`/excelmerge/delete-files/${selectedFolder}/`, {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        console.log("Error in deleting the files ", data.error)
      } else {
        fileList.innerHTML = "No files in the folder";
      }
    })
    .catch((error) => {
      console.log("Failed to delete the files")
    });
});

// Run script for selected folder
runScriptButton.addEventListener("click", () => {
  const selectedFolder = dropdown.value;

  if (!selectedFolder) {
    alert("Please select a folder from the dropdown.");
    return;
  }

  const confirmation = confirm(
    `Are you sure you want to run the script for the folder '${selectedFolder}'?`
  );
  if (!confirmation) return;

  fetch(`/excelmerge/run-script/${selectedFolder}/`, {
    method: "POST",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) {
        scriptStatus.innerHTML = `<li>Error: ${data.error}</li>`;
      } else {
        scriptStatus.innerHTML = `<li>${data.message}</li>`;
      }
    })
    .catch((error) => {
      scriptStatus.innerHTML = `<li>Error: ${error.message}</li>`;
    });
});

// Show/hide elements based on dropdown selection
folderSelect.addEventListener("change", () => {
  const selectedValue = folderSelect.value;
  console.log("Dropdown value changed:", selectedValue);

  if (selectedValue === "Jsons") {
    uploadFormArea.style.display = "none";
    runScriptButton.style.display = "none";
    downloadExcelBtn.style.display = "block";
    roadIdDiv.style.display = "block";
    excelInputDiv.style.display = "block";
  } else {
    uploadFormArea.style.display = "block";
    runScriptButton.style.display = "block";
    downloadExcelBtn.style.display = "none";
    roadIdDiv.style.display = "none";
    excelInputDiv.style.display = "none";
  }
});

// Handle Excel download
downloadExcelBtn.addEventListener("click", () => {
  const roadId = roadIdInput.value.trim();
  const excelName = nameInput.value.trim();

  if (!roadId) {
    alert("Please enter a valid Road ID before downloading.");
    return;
  }

  if (!excelName) {
    alert("Please enter a valid Excel name before downloading.");
    return;
  }

  console.log("Road ID:", roadId);
  console.log("Excel name:", excelName);

  runMergeScript(roadId, excelName);
});

// Function to run the merge script
function runMergeScript(roadId, excelName) {
  fetch("/excelmerge/run_merge_script/", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": getCsrfToken(),
    },
    body: JSON.stringify({ road_id: roadId, name_excel: excelName }),
  })
    .then((response) => {
      console.log("response of the download ", response)
      if (!response.ok) {
        throw new Error("Failed to download the file.");
      }
      return response.blob();
    })
    .then((blob) => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${excelName}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      alert("Excel file downloaded successfully!");
    })
    .catch((error) => {
      console.error("Error downloading the file:", error);
      alert("An error occurred while downloading the file.");
    });
}


function getCsrfToken() {
  return document.querySelector("[name=csrfmiddlewaretoken]").value;
}
