// Driver scorecards functionality
let driverScorecardsData = [];
let selectedPeriod = 'month';
let leaderboardChart = null;

// Format minutes to hours and minutes display
function formatMinutesToHours(minutes) {
    if (!minutes || minutes === 0) return '0m';
    
    const totalMinutes = Math.round(minutes);
    const hours = Math.floor(totalMinutes / 60);
    const remainingMinutes = totalMinutes % 60;
    
    if (hours === 0) {
        return `${remainingMinutes}m`;
    } else if (remainingMinutes === 0) {
        return `${hours}h`;
    } else {
        return `${hours}h ${remainingMinutes}m`;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the scorecards page
    const scorecardsContainer = document.getElementById('scorecards-container');
    if (!scorecardsContainer) return;
    
    // Set up event listeners
    document.querySelectorAll('.period-selector').forEach(button => {
        button.addEventListener('click', function() {
            selectPeriod(this.dataset.period);
        });
    });
    
    // Load initial scorecards data
    loadScorecards();
});

// Load scorecards data from API
function loadScorecards() {
    const url = `/drivers/scorecards/data?period=${selectedPeriod}`;
    
    // Show loading state
    const scorecardsTable = document.getElementById('scorecards-table-body');
    if (scorecardsTable) {
        scorecardsTable.innerHTML = '<tr><td colspan="6" class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></td></tr>';
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            driverScorecardsData = data.scorecards;
            
            // Render scorecards
            renderScorecards();
            
            // Update period display
            updatePeriodDisplay(data.start_date, data.end_date);
            
            // Update leaderboard chart
            updateLeaderboardChart();
            
            // Show confetti for top performers
            celebrateTopPerformers();
        })
        .catch(error => {
            console.error('Error loading scorecards:', error);
            if (scorecardsTable) {
                scorecardsTable.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Failed to load scorecards. Please try again later.</td></tr>';
            }
        });
}

// Render scorecards table
function renderScorecards() {
    const scorecardsTable = document.getElementById('scorecards-table-body');
    if (!scorecardsTable) return;
    
    if (driverScorecardsData.length === 0) {
        scorecardsTable.innerHTML = '<tr><td colspan="6" class="text-center">No scorecard data available for this period.</td></tr>';
        return;
    }
    
    scorecardsTable.innerHTML = '';
    
    driverScorecardsData.forEach(driver => {
        const row = document.createElement('tr');
        
        // Add highlighting for top 3 positions
        if (driver.rank <= 3) {
            row.className = 'table-success';
        }
        
        // Create on-time percentage badges with appropriate colors
        const pickupBadgeClass = getPercentageBadgeClass(driver.on_time_pickup_percentage);
        const deliveryBadgeClass = getPercentageBadgeClass(driver.on_time_delivery_percentage);
        
        row.innerHTML = `
            <td class="text-center">
                ${driver.rank === 1 ? '<i data-feather="award" class="text-warning"></i>' : driver.rank}
            </td>
            <td>
                <a href="/drivers/${driver.driver_id}" class="text-decoration-none">
                    ${driver.name}
                </a>
            </td>
            <td class="text-center">${driver.total_loads}</td>
            <td class="text-center">
                <span class="badge ${pickupBadgeClass}">${driver.on_time_pickup_percentage}%</span>
            </td>
            <td class="text-center">
                <span class="badge ${deliveryBadgeClass}">${driver.on_time_delivery_percentage}%</span>
            </td>
            <td class="text-center">${driver.average_delay_minutes} min</td>
        `;
        
        scorecardsTable.appendChild(row);
    });
    
    // Initialize feather icons
    feather.replace();
}

// Update the leaderboard chart
function updateLeaderboardChart() {
    const chartCanvas = document.getElementById('leaderboard-chart');
    if (!chartCanvas) return;
    
    // Prepare chart data - only show top 10 drivers
    const topDrivers = driverScorecardsData.slice(0, 10);
    
    const labels = topDrivers.map(driver => driver.name);
    const deliveryData = topDrivers.map(driver => driver.on_time_delivery_percentage);
    const pickupData = topDrivers.map(driver => driver.on_time_pickup_percentage);
    
    // Destroy existing chart if it exists
    if (leaderboardChart) {
        leaderboardChart.destroy();
    }
    
    // Create new chart
    leaderboardChart = new Chart(chartCanvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'On-Time Delivery %',
                    data: deliveryData,
                    backgroundColor: 'rgba(255, 99, 132, 0.7)',
                    borderColor: 'rgba(255, 99, 132, 1)',
                    borderWidth: 1
                },
                {
                    label: 'On-Time Pickup %',
                    data: pickupData,
                    backgroundColor: 'rgba(54, 162, 235, 0.7)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    title: {
                        display: true,
                        text: 'On-Time Percentage'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Driver'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: 'Top Performers'
                },
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

// Update date range display
function updatePeriodDisplay(startDate, endDate) {
    const periodDisplay = document.getElementById('period-display');
    if (!periodDisplay) return;
    
    // Format dates
    const start = new Date(startDate);
    const end = new Date(endDate);
    
    const startFormatted = start.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    
    const endFormatted = end.toLocaleDateString(undefined, { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    
    periodDisplay.textContent = `${startFormatted} to ${endFormatted}`;
    
    // Update the active period button
    document.querySelectorAll('.period-selector').forEach(button => {
        if (button.dataset.period === selectedPeriod) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

// Select a different time period
function selectPeriod(period) {
    if (period === selectedPeriod) return;
    
    selectedPeriod = period;
    
    // Update active button
    document.querySelectorAll('.period-selector').forEach(button => {
        if (button.dataset.period === period) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
    
    // Load new data
    loadScorecards();
}

// Get badge class based on percentage
function getPercentageBadgeClass(percentage) {
    if (percentage >= 90) {
        return 'bg-success';
    } else if (percentage >= 75) {
        return 'bg-warning';
    } else {
        return 'bg-danger';
    }
}

// Celebrate top performers with animations
function celebrateTopPerformers() {
    // Only celebrate if there are drivers with good performance
    if (driverScorecardsData.length > 0 && driverScorecardsData[0].on_time_delivery_percentage >= 95) {
        // Show confetti for top performer
        showConfetti();
        
        // Show celebration message
        const message = `${driverScorecardsData[0].name} is the top performer with ${driverScorecardsData[0].on_time_delivery_percentage}% on-time deliveries!`;
        showCelebrationMessage(message);
    }
}

// Show celebration message
function showCelebrationMessage(message) {
    const celebrationElement = document.getElementById('celebration-message');
    if (!celebrationElement) return;
    
    celebrationElement.textContent = message;
    celebrationElement.classList.remove('d-none');
    
    // Add animation class
    celebrationElement.classList.add('celebration-animation');
    
    // Remove animation after it completes
    setTimeout(() => {
        celebrationElement.classList.remove('celebration-animation');
    }, 3000);
}
