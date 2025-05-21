// Dashboard functionality
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the dashboard page
    if (!document.getElementById('dashboard-content')) return;
    
    // Load dashboard data
    loadDashboardSummary();
    loadAtRiskLoads();
    loadPerformanceTrends();
    
    // Set up refresh interval (every 5 minutes)
    setInterval(loadDashboardSummary, 300000);
    setInterval(loadAtRiskLoads, 300000);
});

// Load dashboard summary data
function loadDashboardSummary() {
    fetch('/api/dashboard/summary')
        .then(response => response.json())
        .then(data => {
            // Update active loads count
            document.getElementById('active-loads-count').textContent = data.active_loads;
            
            // Update on-time percentages
            document.getElementById('on-time-pickup-percentage').textContent = data.on_time.pickup_percentage + '%';
            document.getElementById('on-time-delivery-percentage').textContent = data.on_time.delivery_percentage + '%';
            
            // Update pickup progress bar
            const pickupProgressBar = document.getElementById('pickup-progress');
            pickupProgressBar.style.width = data.on_time.pickup_percentage + '%';
            pickupProgressBar.setAttribute('aria-valuenow', data.on_time.pickup_percentage);
            
            // Update delivery progress bar
            const deliveryProgressBar = document.getElementById('delivery-progress');
            deliveryProgressBar.style.width = data.on_time.delivery_percentage + '%';
            deliveryProgressBar.setAttribute('aria-valuenow', data.on_time.delivery_percentage);
            
            // Set appropriate colors based on percentages
            if (data.on_time.pickup_percentage >= 90) {
                pickupProgressBar.classList.remove('bg-warning', 'bg-danger');
                pickupProgressBar.classList.add('bg-success');
            } else if (data.on_time.pickup_percentage >= 75) {
                pickupProgressBar.classList.remove('bg-success', 'bg-danger');
                pickupProgressBar.classList.add('bg-warning');
            } else {
                pickupProgressBar.classList.remove('bg-success', 'bg-warning');
                pickupProgressBar.classList.add('bg-danger');
            }
            
            if (data.on_time.delivery_percentage >= 90) {
                deliveryProgressBar.classList.remove('bg-warning', 'bg-danger');
                deliveryProgressBar.classList.add('bg-success');
            } else if (data.on_time.delivery_percentage >= 75) {
                deliveryProgressBar.classList.remove('bg-success', 'bg-danger');
                deliveryProgressBar.classList.add('bg-warning');
            } else {
                deliveryProgressBar.classList.remove('bg-success', 'bg-warning');
                deliveryProgressBar.classList.add('bg-danger');
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
            
            // Play a success sound if metrics are good
            if (data.on_time.pickup_percentage >= 95 && data.on_time.delivery_percentage >= 95) {
                playSuccessSound();
                showConfetti();
            }
        })
        .catch(error => console.error('Error loading dashboard summary:', error));
}

// Load at-risk loads
function loadAtRiskLoads() {
    fetch('/api/dashboard/at_risk_loads')
        .then(response => response.json())
        .then(loads => {
            const atRiskTable = document.getElementById('at-risk-loads-table');
            const atRiskBody = document.getElementById('at-risk-loads-body');
            
            if (atRiskBody) {
                atRiskBody.innerHTML = '';
                
                if (loads && loads.length > 0) {
                    atRiskTable.classList.remove('d-none');
                    
                    loads.forEach(load => {
                        const row = document.createElement('tr');
                        
                        // Set row color based on delay severity
                        if (load.delay_minutes > 120) {
                            row.className = 'table-danger';
                        } else if (load.delay_minutes > 60) {
                            row.className = 'table-warning';
                        }
                        
                        row.innerHTML = `
                            <td><a href="/loads/${load.id}">${load.reference_number}</a></td>
                            <td>${load.driver_name}</td>
                            <td>${formatDateTime(load.scheduled_delivery)}</td>
                            <td>${formatDateTime(load.current_eta)}</td>
                            <td>${load.delay_minutes} min</td>
                        `;
                        
                        atRiskBody.appendChild(row);
                    });
                } else {
                    atRiskTable.classList.add('d-none');
                    document.getElementById('no-at-risk-loads').classList.remove('d-none');
                }
            }
        })
        .catch(error => console.error('Error loading at-risk loads:', error));
}

// Load performance trends
function loadPerformanceTrends() {
    fetch('/api/dashboard/performance_trends')
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
            
            // Create the performance chart
            const ctx = document.getElementById('performance-chart');
            if (ctx) {
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: dates,
                        datasets: [
                            {
                                label: 'On-Time Pickup %',
                                data: pickupPercentages,
                                borderColor: 'rgba(54, 162, 235, 1)',
                                backgroundColor: 'rgba(54, 162, 235, 0.2)',
                                tension: 0.1,
                                yAxisID: 'y'
                            },
                            {
                                label: 'On-Time Delivery %',
                                data: deliveryPercentages,
                                borderColor: 'rgba(255, 99, 132, 1)',
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                tension: 0.1,
                                yAxisID: 'y'
                            },
                            {
                                label: 'Total Loads',
                                data: loadCounts,
                                borderColor: 'rgba(75, 192, 192, 1)',
                                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                tension: 0.1,
                                yAxisID: 'y1'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        interaction: {
                            mode: 'index',
                            intersect: false,
                        },
                        plugins: {
                            title: {
                                display: true,
                                text: '30-Day Performance Trends'
                            }
                        },
                        scales: {
                            y: {
                                type: 'linear',
                                display: true,
                                position: 'left',
                                title: {
                                    display: true,
                                    text: 'Percentage'
                                },
                                min: 0,
                                max: 100
                            },
                            y1: {
                                type: 'linear',
                                display: true,
                                position: 'right',
                                title: {
                                    display: true,
                                    text: 'Load Count'
                                },
                                min: 0,
                                grid: {
                                    drawOnChartArea: false
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
    // This would play a success sound if needed
    // For now, we'll just log it
    console.log('Playing success sound');
}
