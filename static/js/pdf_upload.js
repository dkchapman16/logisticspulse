// PDF upload and processing functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check if PDF upload elements exist on the page
    const pdfUploadForm = document.getElementById('ratecon-upload-form');
    if (!pdfUploadForm) return;
    
    // Set up event listeners for the PDF upload form
    pdfUploadForm.addEventListener('submit', handlePdfUpload);
    
    // Set up drag and drop functionality
    setupDragAndDrop();
    
    // Initialize file input change listener
    const fileInput = document.getElementById('ratecon-file');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            updateFileLabel(this);
        });
    }
});

// Handle PDF upload form submission
function handlePdfUpload(event) {
    event.preventDefault();
    
    const form = event.target;
    const fileInput = form.querySelector('#ratecon-file');
    const submitButton = form.querySelector('button[type="submit"]');
    const statusElement = document.getElementById('upload-status');
    
    // Check if a file was selected
    if (!fileInput.files || fileInput.files.length === 0) {
        showUploadError('Please select a file to upload.');
        return;
    }
    
    // Check if the file is a PDF
    const file = fileInput.files[0];
    if (!file.type.includes('pdf')) {
        showUploadError('Please upload a PDF file.');
        return;
    }
    
    // Show loading state
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    statusElement.innerHTML = 'Extracting data from PDF...';
    statusElement.className = 'alert alert-info';
    
    // Create form data and submit
    const formData = new FormData();
    formData.append('ratecon_file', file);
    
    fetch('/loads/upload-ratecon', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        // Reset loading state
        submitButton.disabled = false;
        submitButton.innerHTML = 'Upload RateCon';
        
        if (data.success) {
            // Show success message
            statusElement.innerHTML = 'Data extracted successfully!';
            statusElement.className = 'alert alert-success';
            
            // Display the extracted data
            displayExtractedData(data.data);
            
            // Reset form
            form.reset();
            document.querySelector('.custom-file-label').textContent = 'Choose file...';
        } else {
            showUploadError(data.error || 'Failed to process PDF.');
        }
    })
    .catch(error => {
        console.error('Error uploading PDF:', error);
        submitButton.disabled = false;
        submitButton.innerHTML = 'Upload RateCon';
        showUploadError('Error processing file: ' + error.message);
    });
}

// Display extracted data from the PDF
function displayExtractedData(data) {
    const extractedDataContainer = document.getElementById('extracted-data');
    if (!extractedDataContainer) return;
    
    // Make the container visible
    extractedDataContainer.classList.remove('d-none');
    
    // Populate form fields with extracted data
    if (data.reference_number) {
        const refField = document.getElementById('reference_number');
        if (refField) refField.value = data.reference_number;
    }
    
    if (data.pickup) {
        const pickupNameField = document.getElementById('pickup_facility_name');
        const pickupAddrField = document.getElementById('pickup_address');
        const pickupTimeField = document.getElementById('scheduled_pickup_time');
        
        if (pickupNameField && data.pickup.facility_name) {
            pickupNameField.value = data.pickup.facility_name;
        }
        if (pickupAddrField && data.pickup.address) {
            pickupAddrField.value = data.pickup.address;
        }
        if (pickupTimeField && data.pickup.scheduled_time) {
            pickupTimeField.value = data.pickup.scheduled_time;
        }
    }
    
    if (data.delivery) {
        const deliveryNameField = document.getElementById('delivery_facility_name');
        const deliveryAddrField = document.getElementById('delivery_address');
        const deliveryTimeField = document.getElementById('scheduled_delivery_time');
        
        if (deliveryNameField && data.delivery.facility_name) {
            deliveryNameField.value = data.delivery.facility_name;
        }
        if (deliveryAddrField && data.delivery.address) {
            deliveryAddrField.value = data.delivery.address;
        }
        if (deliveryTimeField && data.delivery.scheduled_time) {
            deliveryTimeField.value = data.delivery.scheduled_time;
        }
    }
    
    if (data.client && data.client.name) {
        const clientField = document.getElementById('client_name');
        if (clientField) clientField.value = data.client.name;
    }
    
    // Show raw text for debugging if needed
    if (data.raw_text) {
        const rawTextContainer = document.getElementById('raw-text-preview');
        if (rawTextContainer) {
            rawTextContainer.innerHTML = `<pre>${data.raw_text}</pre>`;
        }
    }
    populateFormField('reference-number', data.reference_number);
    
    // Populate client info
    if (data.client && data.client.name) {
        const clientSelect = document.getElementById('client-id');
        if (clientSelect) {
            // Try to find a matching client by name
            const clientOptions = Array.from(clientSelect.options);
            const matchingOption = clientOptions.find(option => 
                option.text.toLowerCase().includes(data.client.name.toLowerCase())
            );
            
            if (matchingOption) {
                clientSelect.value = matchingOption.value;
            }
        }
    }
    
    // Populate pickup information
    if (data.pickup) {
        if (data.pickup.address) {
            populateFormField('pickup-address', data.pickup.address);
            
            // Try to match a facility
            findMatchingFacility(data.pickup.address, 'pickup-facility-id');
        }
        
        if (data.pickup.date_time) {
            populateFormField('scheduled-pickup-time', formatDateTimeForInput(data.pickup.date_time));
        }
        
        if (data.pickup.coordinates) {
            populateFormField('pickup-lat', data.pickup.coordinates.lat);
            populateFormField('pickup-lng', data.pickup.coordinates.lng);
        }
    }
    
    // Populate delivery information
    if (data.delivery) {
        if (data.delivery.address) {
            populateFormField('delivery-address', data.delivery.address);
            
            // Try to match a facility
            findMatchingFacility(data.delivery.address, 'delivery-facility-id');
        }
        
        if (data.delivery.date_time) {
            populateFormField('scheduled-delivery-time', formatDateTimeForInput(data.delivery.date_time));
        }
        
        if (data.delivery.coordinates) {
            populateFormField('delivery-lat', data.delivery.coordinates.lat);
            populateFormField('delivery-lng', data.delivery.coordinates.lng);
        }
    }
    
    // Scroll to the extracted data section
    extractedDataContainer.scrollIntoView({ behavior: 'smooth' });
    
    // Show a success animation
    showSuccessAnimation();
}

// Try to find a matching facility in the dropdown
function findMatchingFacility(address, selectId) {
    const facilitySelect = document.getElementById(selectId);
    if (!facilitySelect || !address) return;
    
    // Normalize the address for comparison
    const normalizedAddress = address.toLowerCase().replace(/\s+/g, ' ').trim();
    
    // Try to find a matching facility
    const facilityOptions = Array.from(facilitySelect.options);
    const matchingOption = facilityOptions.find(option => {
        if (option.dataset.address) {
            const optionAddress = option.dataset.address.toLowerCase().replace(/\s+/g, ' ').trim();
            return optionAddress.includes(normalizedAddress) || normalizedAddress.includes(optionAddress);
        }
        return false;
    });
    
    if (matchingOption) {
        facilitySelect.value = matchingOption.value;
        
        // Trigger a change event to update any dependent fields
        const event = new Event('change');
        facilitySelect.dispatchEvent(event);
    }
}

// Populate a form field with extracted data
function populateFormField(fieldId, value) {
    const field = document.getElementById(fieldId);
    if (field && value) {
        field.value = value;
        
        // Add a highlight effect
        field.classList.add('bg-success', 'bg-opacity-25');
        setTimeout(() => {
            field.classList.remove('bg-success', 'bg-opacity-25');
        }, 3000);
    }
}

// Format date and time for input fields
function formatDateTimeForInput(dateTimeStr) {
    if (!dateTimeStr) return '';
    
    try {
        const date = new Date(dateTimeStr);
        
        // Format as YYYY-MM-DDTHH:MM
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day}T${hours}:${minutes}`;
    } catch (error) {
        console.error('Error formatting date:', error);
        return '';
    }
}

// Set up drag and drop functionality
function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    if (!dropZone) return;
    
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        dropZone.classList.add('drag-highlight');
    }
    
    function unhighlight() {
        dropZone.classList.remove('drag-highlight');
    }
    
    dropZone.addEventListener('drop', handleDrop, false);
    
    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        
        if (files && files.length > 0) {
            const fileInput = document.getElementById('ratecon-file');
            fileInput.files = files;
            updateFileLabel(fileInput);
        }
    }
}

// Update file input label to show selected file name
function updateFileLabel(input) {
    const label = input.nextElementSibling;
    if (label) {
        if (input.files && input.files.length > 0) {
            label.textContent = input.files[0].name;
        } else {
            label.textContent = 'Choose file...';
        }
    }
}

// Show error message for PDF upload
function showUploadError(message) {
    const statusElement = document.getElementById('upload-status');
    if (statusElement) {
        statusElement.innerHTML = message;
        statusElement.className = 'alert alert-danger';
    }
}

// Show success animation after extraction
function showSuccessAnimation() {
    // This would show a success animation
    // For now, we'll use the animations.js confetti function
    if (typeof showConfetti === 'function') {
        showConfetti();
    }
}
