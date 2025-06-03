// Dashboard functionality
let currentViewMode = 'company'; // 'company' or 'driver'
let currentDateRange = '30'; // days or 'custom'
let selectedDriverId = null;
let customStartDate = '2025-05-01';
let customEndDate = '2025-05-31';
let performanceChart = null; // Global chart instance

// Get current driver ID if viewing individual driver
function getCurrentDriverId() {
    return selectedDriverId;
}

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the dashboard page
    if (!document.getElementById('dashboard-content')) return;
    
    // Initialize dashboard controls
    initializeDashboardControls();
    initializeSafeModeToggle();
    
    // Load dashboard data
    loadDashboardSummary();
    loadAtRiskLoads();
    loadPerformanceTrends();
    

    
    // Apply slot machine effect to stats on initial load
    setTimeout(() => {
        // Get all elements with slot machine effect class
        const slotElements = document.querySelectorAll('.slot-machine-effect');
        slotElements.forEach(element => {
            // Get current value and apply slot machine animation
            const currentValue = element.textContent;
            if (currentValue.includes('%')) {
                showSlotMachineEffect(element, parseInt(currentValue), '', '%');
            } else {
                showSlotMachineEffect(element, currentValue);
            }
        });
    }, 500);
    
    // Set up refresh interval (every 5 minutes)
    setInterval(loadDashboardSummary, 300000);
    setInterval(loadAtRiskLoads, 300000);
});

// Initialize dashboard controls
function initializeDashboardControls() {
    // Load available drivers for dropdown
    loadDriverOptions();
    
    // View toggle (Company vs Individual)
    const companyViewBtn = document.getElementById('company-view');
    const driverViewBtn = document.getElementById('driver-view');
    const driverSelect = document.getElementById('driver-select');
    
    if (companyViewBtn && driverViewBtn) {
        companyViewBtn.addEventListener('change', function() {
            if (this.checked) {
                currentViewMode = 'company';
                selectedDriverId = null;
                driverSelect.classList.add('d-none');
                refreshDashboard();
            }
        });
        
        driverViewBtn.addEventListener('change', function() {
            if (this.checked) {
                currentViewMode = 'driver';
                driverSelect.classList.remove('d-none');
                // Don't refresh until driver is selected
            }
        });
    }
    
    // Driver selection
    if (driverSelect) {
        driverSelect.addEventListener('change', function() {
            selectedDriverId = this.value;
            if (selectedDriverId && currentViewMode === 'driver') {
                refreshDashboard();
            }
        });
    }
    
    // Date range selection
    const dateRangeSelect = document.getElementById('date-range-select');
    const customDateControls = document.getElementById('custom-date-controls');
    
    if (dateRangeSelect) {
        dateRangeSelect.addEventListener('change', function() {
            currentDateRange = this.value;
            
            if (this.value === 'custom') {
                customDateControls.classList.remove('d-none');
            } else {
                customDateControls.classList.add('d-none');
                refreshDashboard();
            }
        });
    }
    
    // Custom date range apply
    const applyCustomRange = document.getElementById('apply-custom-range');
    const startDate = document.getElementById('start-date');
    const endDate = document.getElementById('end-date');
    
    if (applyCustomRange) {
        applyCustomRange.addEventListener('click', function() {
            customStartDate = startDate.value;
            customEndDate = endDate.value;
            
            if (customStartDate && customEndDate) {
                refreshDashboard();
            }
        });
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refresh-dashboard');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            refreshDashboard();
        });
    }
}

// Load driver options for dropdown
function loadDriverOptions() {
    fetch('/drivers/data')
        .then(response => response.json())
        .then(data => {
            const driverSelect = document.getElementById('driver-select');
            if (driverSelect && data.drivers) {
                // Clear existing options except first
                driverSelect.innerHTML = '<option value="">Select Driver...</option>';
                
                data.drivers.forEach(driver => {
                    const option = document.createElement('option');
                    option.value = driver.id;
                    option.textContent = driver.name;
                    driverSelect.appendChild(option);
                });
            }
        })
        .catch(error => {
            console.error('Error loading drivers:', error);
        });
}

// Refresh dashboard with current settings
function refreshDashboard() {
    loadDashboardSummary();
    loadAtRiskLoads();
    loadPerformanceTrends();
}

// Initialize Safe Mode toggle functionality
function initializeSafeModeToggle() {
    const safeModeToggle = document.getElementById('safe-mode-toggle');
    if (safeModeToggle) {
        // Load saved state from localStorage
        const savedState = localStorage.getItem('freightpace-safe-mode');
        if (savedState === 'true') {
            safeModeToggle.checked = true;
            showSafeModeNotification();
        }
        
        // Handle toggle changes
        safeModeToggle.addEventListener('change', function() {
            const isEnabled = this.checked;
            localStorage.setItem('freightpace-safe-mode', isEnabled.toString());
            
            if (isEnabled) {
                showSafeModeNotification();
            } else {
                hideSafeModeNotification();
            }
        });
    }
}

// Show safe mode notification
function showSafeModeNotification() {
    // Remove existing notification
    const existing = document.getElementById('safe-mode-notification');
    if (existing) existing.remove();
    
    // Create notification
    const notification = document.createElement('div');
    notification.id = 'safe-mode-notification';
    notification.className = 'alert alert-warning d-flex align-items-center mb-3';
    notification.innerHTML = `
        <i data-feather="shield" class="me-2"></i>
        <span>Safe mode enabled – no API calls will be made during PDF processing.</span>
    `;
    
    // Insert after dashboard header
    const dashboardHeader = document.querySelector('.d-flex.justify-content-between.align-items-center.mb-4');
    if (dashboardHeader) {
        dashboardHeader.insertAdjacentElement('afterend', notification);
        feather.replace(); // Refresh feather icons
    }
}

// Hide safe mode notification
function hideSafeModeNotification() {
    const notification = document.getElementById('safe-mode-notification');
    if (notification) {
        notification.remove();
    }
}

// Load dashboard summary data
function loadDashboardSummary() {
    // Build query parameters based on current settings
    const params = new URLSearchParams();
    
    // Add date range parameters
    if (currentDateRange === 'custom') {
        params.append('start_date', customStartDate);
        params.append('end_date', customEndDate);
    } else {
        params.append('period', currentDateRange);
    }
    
    // Add driver filter if in individual view mode
    if (currentViewMode === 'driver' && selectedDriverId) {
        params.append('driver_id', selectedDriverId);
    }
    
    fetch(`/api/dashboard/summary?${params.toString()}`)
        .then(response => response.json())
        .then(data => {
            console.log('Dashboard data loaded:', data);
            
            // Update total deliveries count (using the DELIVERIES card)
            const totalDeliveriesElement = document.getElementById('active-loads-count');
            if (totalDeliveriesElement && data.total_deliveries !== undefined) {
                showSlotMachineEffect(totalDeliveriesElement, data.total_deliveries);
            }
            
            // Show/hide company stats based on view mode
            const companyStatsElement = document.getElementById('company-stats');
            if (companyStatsElement) {
                if (currentViewMode === 'driver' && selectedDriverId) {
                    // Hide company stats in individual driver view
                    companyStatsElement.style.display = 'none';
                    companyStatsElement.style.visibility = 'hidden';
                    companyStatsElement.classList.add('d-none');
                } else {
                    // Show company stats in company view
                    companyStatsElement.style.display = 'flex';
                    companyStatsElement.style.visibility = 'visible';
                    companyStatsElement.classList.remove('d-none');
                    
                    // Update driver count and top driver info if available
                    const totalDriversElement = document.getElementById('total-drivers-count');
                    const topDriverElement = document.getElementById('top-driver-info');
                    
                    if (totalDriversElement && data.total_drivers !== undefined) {
                        totalDriversElement.textContent = data.total_drivers;
                    }
                    
                    if (topDriverElement && data.top_drivers && data.top_drivers.length > 0) {
                        const topDriver = data.top_drivers[0];
                        topDriverElement.textContent = `${topDriver.name} (${Math.round(topDriver.on_time_percentage)}%)`;
                    }
                }
            }
            
            // Update on-time data for toggle functionality
            if (typeof window.updateOnTimeData === 'function') {
                window.updateOnTimeData(data);
            }
            
            // Legacy support - update old element if it exists (for backward compatibility)
            const onTimeDeliveryElement = document.getElementById('on-time-delivery-percentage');
            if (onTimeDeliveryElement) {
                const percentValue = Math.ceil(data.on_time.delivery_percentage);
                onTimeDeliveryElement.textContent = percentValue;
                
                // Find the parent circular-metric element and update the --percent CSS variable
                const circularMetric = onTimeDeliveryElement.closest('.circular-metric');
                const circularMetricValue = circularMetric?.querySelector('.circular-metric-value');
                
                if (circularMetric) {
                    circularMetric.style.setProperty('--percent', percentValue);
                }
                
                // Apply colors and effects based on performance
                const progressCircle = circularMetric?.querySelector('.progress-circle');
                
                if (percentValue >= 85) {
                    // Excellent performance - Green
                    if (circularMetricValue) {
                        circularMetricValue.style.color = '#00c48c';
                        circularMetricValue.style.textShadow = '0 0 15px rgba(0, 196, 140, 0.6)';
                    }
                    if (progressCircle) progressCircle.style.stroke = '#00c48c';
                } else if (percentValue >= 70) {
                    // Warning performance - Yellow/Gold
                    if (circularMetricValue) {
                        circularMetricValue.style.color = '#FFD700';
                        circularMetricValue.style.textShadow = '0 0 15px rgba(255, 215, 0, 0.6)';
                    }
                    if (progressCircle) progressCircle.style.stroke = '#FFD700';
                } else {
                    // Poor performance - Red
                    if (circularMetricValue) {
                        circularMetricValue.style.color = '#ff5757';
                        circularMetricValue.style.textShadow = '0 0 15px rgba(255, 87, 87, 0.6)';
                    }
                    if (progressCircle) progressCircle.style.stroke = '#ff5757';
                }
            }
            
            // Update late loads count using actual data
            const lateLoadsElement = document.getElementById('late-loads-count');
            if (lateLoadsElement && data.late_deliveries !== undefined) {
                showSlotMachineEffect(lateLoadsElement, data.late_deliveries);
            }
            

            
            // Update top drivers list
            const topDriversList = document.getElementById('top-drivers-list');
            if (topDriversList) {
                topDriversList.innerHTML = '';
                
                if (data.top_drivers && data.top_drivers.length > 0) {
                    data.top_drivers.forEach(driver => {
                        const listItem = document.createElement('a');
                        listItem.href = `/drivers/${driver.id}`;
                        listItem.className = 'list-group-item list-group-item-action d-flex justify-content-between align-items-center';
                        
                        listItem.innerHTML = `
                            <div>
                                <i data-feather="user"></i>
                                <span class="ms-2">${driver.name}</span>
                            </div>
                            <span class="badge bg-primary rounded-pill">${driver.on_time_percentage}%</span>
                        `;
                        
                        topDriversList.appendChild(listItem);
                    });
                    
                    // Re-initialize Feather icons
                    feather.replace();
                } else {
                    topDriversList.innerHTML = '<div class="list-group-item">No driver data available</div>';
                }
            }
            
            // Update recent notifications
            const notificationsList = document.getElementById('recent-notifications');
            if (notificationsList) {
                notificationsList.innerHTML = '';
                
                if (data.notifications && data.notifications.length > 0) {
                    data.notifications.forEach(notification => {
                        const listItem = document.createElement('div');
                        listItem.className = 'list-group-item';
                        
                        // Set background color based on notification type
                        if (notification.type === 'warning') {
                            listItem.classList.add('list-group-item-warning');
                        } else if (notification.type === 'danger') {
                            listItem.classList.add('list-group-item-danger');
                        } else if (notification.type === 'success') {
                            listItem.classList.add('list-group-item-success');
                        } else {
                            listItem.classList.add('list-group-item-info');
                        }
                        
                        listItem.innerHTML = `
                            <div class="d-flex w-100 justify-content-between">
                                <small>${notification.created_at}</small>
                            </div>
                            <p class="mb-1">${notification.message}</p>
                        `;
                        
                        notificationsList.appendChild(listItem);
                    });
                } else {
                    notificationsList.innerHTML = '<div class="list-group-item">No recent notifications</div>';
                }
            }
            
            // Play a success sound if metrics are good (disabled)
            if (data.on_time.pickup_percentage >= 95 && data.on_time.delivery_percentage >= 95) {
                // playSuccessSound(); // Disabled audio notifications
                showConfetti();
            }
        })
        .catch(error => console.error('Error loading dashboard summary:', error));
}

// Load at-risk loads
function loadAtRiskLoads() {
    // Get current driver ID if viewing individual driver
    const currentDriverId = getCurrentDriverId();
    const url = currentDriverId ? 
        `/api/dashboard/at_risk_loads?driver_id=${currentDriverId}` : 
        '/api/dashboard/at_risk_loads';
    
    fetch(url)
        .then(response => response.json())
        .then(loads => {
            const atRiskContent = document.getElementById('at-risk-loads-content');
            const noAtRiskDiv = document.getElementById('no-at-risk-loads');
            
            if (atRiskContent) {
                atRiskContent.innerHTML = '';
                
                if (loads && loads.length > 0) {
                    noAtRiskDiv.classList.add('d-none');
                    
                    loads.forEach(load => {
                        const isDelayed = load.risk_class === 'danger';
                        const borderColor = isDelayed ? 'var(--highlight-alert)' : 'var(--celebration-gold)';
                        const bgColor = isDelayed ? 'rgba(255, 87, 87, 0.1)' : 'rgba(255, 215, 0, 0.1)';
                        const badgeColor = isDelayed ? 'var(--highlight-alert)' : 'var(--celebration-gold)';
                        const badgeTextColor = isDelayed ? '#fff' : '#000';
                        
                        const loadDiv = document.createElement('div');
                        loadDiv.className = 'at-risk-load-item mb-3 p-3';
                        loadDiv.style.cssText = `background-color: ${bgColor}; border-radius: 8px; border-left: 3px solid ${borderColor};`;
                        
                        loadDiv.innerHTML = `
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <a href="/loads/${load.id}" class="clickable-ref" style="color: var(--bright-text); font-weight: 600; text-decoration: none; cursor: pointer; transition: color 0.2s;">${load.reference_number}</a>
                                <span class="badge" style="background-color: ${badgeColor}; color: ${badgeTextColor};">${load.risk_label}</span>
                            </div>
                            <div class="d-flex justify-content-between mb-2">
                                <div>
                                    <div style="color: var(--neutral-text); font-size: 0.8rem;">ORIGIN-DESTINATION</div>
                                    <div style="color: var(--bright-text);">${load.origin} → ${load.destination}</div>
                                </div>
                                <div class="text-end">
                                    <div style="color: var(--neutral-text); font-size: 0.8rem;">DRIVER</div>
                                    <a href="/drivers/${load.driver_id}" class="clickable-driver" style="color: var(--bright-text); text-decoration: none; cursor: pointer; transition: color 0.2s;">${load.driver_name}</a>
                                </div>
                            </div>
                            <div class="progress" style="height: 4px; background-color: rgba(255, 255, 255, 0.1);">
                                <div class="progress-bar" role="progressbar" style="width: ${isDelayed ? '75' : '85'}%; background-color: ${borderColor};" aria-valuenow="${isDelayed ? '75' : '85'}" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                        `;
                        
                        atRiskContent.appendChild(loadDiv);
                    });
                } else {
                    noAtRiskDiv.classList.remove('d-none');
                }
            }
        })
        .catch(error => console.error('Error loading at-risk loads:', error));
}

// Load performance trends
function loadPerformanceTrends() {
    // Get current driver ID if viewing individual driver
    const currentDriverId = getCurrentDriverId();
    const url = currentDriverId ? 
        `/api/dashboard/performance_trends?driver_id=${currentDriverId}` : 
        '/api/dashboard/performance_trends';
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (!data || data.length === 0) return;
            
            // Prepare data for chart
            const dates = [];
            const pickupPercentages = [];
            const deliveryPercentages = [];
            const loadCounts = [];
            
            data.forEach(entry => {
                dates.push(formatDate(entry.date));
                pickupPercentages.push(entry.on_time_pickup_percentage);
                deliveryPercentages.push(entry.on_time_delivery_percentage);
                loadCounts.push(entry.loads);
            });
            
            // Create the Tesla-style performance chart
            const ctx = document.getElementById('performance-chart');
            if (ctx) {
                // Destroy existing chart if it exists
                if (performanceChart) {
                    performanceChart.destroy();
                    performanceChart = null;
                }
                
                // Define chart gradient fills
                const chartContext = ctx.getContext('2d');
                
                // Create glowing mint green gradient for primary line
                const primaryGradient = chartContext.createLinearGradient(0, 0, 0, 300);
                primaryGradient.addColorStop(0, 'rgba(0, 196, 140, 0.5)');
                primaryGradient.addColorStop(1, 'rgba(0, 196, 140, 0)');
                
                // Create glowing gold gradient for secondary line
                const secondaryGradient = chartContext.createLinearGradient(0, 0, 0, 300);
                secondaryGradient.addColorStop(0, 'rgba(255, 215, 0, 0.3)');
                secondaryGradient.addColorStop(1, 'rgba(255, 215, 0, 0)');
                
                // Configure Chart.js with dark mode defaults
                Chart.defaults.color = 'rgba(255, 255, 255, 0.7)';
                Chart.defaults.borderColor = 'rgba(255, 255, 255, 0.1)';
                
                performanceChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [
                            {
                                label: 'On-Time Delivery',
                                data: deliveryPercentages,
                                borderColor: '#00C48C', // FreightPace mint green
                                backgroundColor: primaryGradient,
                                borderWidth: 3,
                                pointBackgroundColor: '#00C48C',
                                pointBorderColor: '#00C48C',
                                pointHoverBackgroundColor: '#FFFFFF',
                                pointHoverBorderColor: '#00C48C',
                                pointRadius: 4,
                                pointHoverRadius: 6,
                                tension: 0.4,
                                fill: true,
                                yAxisID: 'y'
                            },
                            {
                                label: 'On-Time Pickup',
                                data: pickupPercentages,
                                borderColor: '#FFD700', // Gold
                                backgroundColor: secondaryGradient,
                                borderWidth: 3,
                                pointBackgroundColor: '#FFD700',
                                pointBorderColor: '#FFD700',
                                pointHoverBackgroundColor: '#FFFFFF',
                                pointHoverBorderColor: '#FFD700',
                                pointRadius: 4,
                                pointHoverRadius: 6,
                                tension: 0.4,
                                fill: true,
                                yAxisID: 'y'
                            },
                            {
                                label: 'Total Loads',
                                data: loadCounts,
                                borderColor: 'rgba(255, 255, 255, 0.5)', // White with opacity
                                borderWidth: 2,
                                borderDash: [5, 5],
                                pointBackgroundColor: 'rgba(255, 255, 255, 0.8)',
                                pointBorderColor: 'rgba(255, 255, 255, 0.8)',
                                pointRadius: 3,
                                tension: 0.4,
                                fill: false,
                                yAxisID: 'y1'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        layout: {
                            padding: {
                                top: 30,
                                bottom: 20,
                                left: 20,
                                right: 20
                            }
                        },
                        interaction: {
                            mode: 'index',
                            intersect: false,
                        },
                        plugins: {
                            legend: {
                                position: 'top',
                                labels: {
                                    boxWidth: 12,
                                    usePointStyle: true,
                                    pointStyle: 'circle',
                                    padding: 20,
                                    color: 'rgba(255, 255, 255, 0.7)'
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(30, 31, 37, 0.9)',
                                titleColor: '#FFFFFF',
                                bodyColor: '#FFFFFF',
                                borderColor: 'rgba(0, 196, 140, 0.5)',
                                borderWidth: 1,
                                padding: 12,
                                boxPadding: 6,
                                usePointStyle: true,
                                bodyFont: {
                                    family: "'Inter', sans-serif"
                                },
                                titleFont: {
                                    family: "'Inter', sans-serif",
                                    weight: 'bold'
                                }
                            }
                        },
                        scales: {
                            x: {
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    drawBorder: false
                                },
                                ticks: {
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 10
                                    }
                                }
                            },
                            y: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: 'ON-TIME PERCENTAGE',
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 10,
                                        weight: 'bold'
                                    }
                                },
                                min: 0,
                                max: 100,
                                grid: {
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    drawBorder: false
                                },
                                ticks: {
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 10
                                    }
                                }
                            },
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {
                                    display: true,
                                    text: 'LOAD COUNT',
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 10,
                                        weight: 'bold'
                                    }
                                },
                                min: 0,
                                grid: {
                                    drawOnChartArea: false,
                                    color: 'rgba(255, 255, 255, 0.05)',
                                    drawBorder: false
                                },
                                ticks: {
                                    color: 'rgba(255, 255, 255, 0.5)',
                                    font: {
                                        family: "'Inter', sans-serif",
                                        size: 10
                                    }
                                }
                            }
                        }
                    }
                });
            }
        })
        .catch(error => console.error('Error loading performance trends:', error));
}

// Helper function to format date and time
function formatDateTime(dateTimeStr) {
    if (!dateTimeStr) return 'N/A';
    
    const date = new Date(dateTimeStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Helper function to format just the date
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    
    const date = new Date(dateStr);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// Play success sound for achievements
function playSuccessSound() {
    // Use the success sound function from animations.js
    if (typeof window.playSuccessSound === 'function') {
        window.playSuccessSound();
    } else {
        console.log('Playing success sound');
    }
}

// Initialize streak tracker with sample data (in a real app, this would come from the server)



