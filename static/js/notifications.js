// Notifications functionality
let notificationsData = [];
let currentPage = 1;
let totalPages = 1;
let unreadOnly = false;

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the notifications page
    const notificationsContainer = document.getElementById('notifications-container');
    if (!notificationsContainer) return;
    
    // Set up event listeners
    document.getElementById('mark-all-read-btn')?.addEventListener('click', markAllAsRead);
    document.getElementById('unread-filter')?.addEventListener('change', toggleUnreadFilter);
    document.getElementById('notifications-previous')?.addEventListener('click', loadPreviousPage);
    document.getElementById('notifications-next')?.addEventListener('click', loadNextPage);
    
    // Load initial notifications
    loadNotifications();
});

// Load notifications data
function loadNotifications(page = 1) {
    currentPage = page;
    const url = `/notifications/data?page=${page}&unread_only=${unreadOnly}`;
    
    // Show loading state
    const notificationsList = document.getElementById('notifications-list');
    if (notificationsList) {
        notificationsList.innerHTML = '<div class="d-flex justify-content-center my-5"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            notificationsData = data.notifications;
            totalPages = data.pages;
            
            // Update unread count badge
            const unreadBadge = document.querySelector('.notification-badge');
            if (unreadBadge) {
                if (data.unread_count > 0) {
                    unreadBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                    unreadBadge.classList.remove('d-none');
                } else {
                    unreadBadge.classList.add('d-none');
                }
            }
            
            // Render notifications
            renderNotifications();
            
            // Update pagination
            updatePagination(data.page, data.pages);
        })
        .catch(error => {
            console.error('Error loading notifications:', error);
            if (notificationsList) {
                notificationsList.innerHTML = '<div class="alert alert-danger">Failed to load notifications. Please try again later.</div>';
            }
        });
}

// Render notifications list
function renderNotifications() {
    const notificationsList = document.getElementById('notifications-list');
    if (!notificationsList) return;
    
    if (notificationsData.length === 0) {
        notificationsList.innerHTML = '<div class="text-center p-4">No notifications to display.</div>';
        return;
    }
    
    notificationsList.innerHTML = '';
    
    notificationsData.forEach(notification => {
        const notificationCard = document.createElement('div');
        notificationCard.className = `card mb-3 ${notification.read ? 'opacity-75' : 'border-primary'}`;
        notificationCard.dataset.notificationId = notification.id;
        
        // Determine notification color based on type
        let badgeClass = 'bg-info';
        let iconName = 'info';
        
        if (notification.type === 'warning') {
            badgeClass = 'bg-warning';
            iconName = 'alert-triangle';
        } else if (notification.type === 'danger') {
            badgeClass = 'bg-danger';
            iconName = 'alert-octagon';
        } else if (notification.type === 'success') {
            badgeClass = 'bg-success';
            iconName = 'check-circle';
        }
        
        let relatedContent = '';
        if (notification.load) {
            relatedContent += `<a href="/loads/${notification.load.id}" class="btn btn-sm btn-outline-primary">View Load</a>`;
        }
        if (notification.driver) {
            relatedContent += `<a href="/drivers/${notification.driver.id}" class="btn btn-sm btn-outline-primary ms-2">View Driver</a>`;
        }
        
        notificationCard.innerHTML = `
            <div class="card-header d-flex justify-content-between align-items-center">
                <div>
                    <span class="badge ${badgeClass}"><i data-feather="${iconName}"></i></span>
                    <small class="ms-2 text-muted">${notification.created_at}</small>
                </div>
                <div>
                    ${!notification.read ? `<button class="btn btn-sm btn-outline-primary mark-read-btn" data-id="${notification.id}">Mark Read</button>` : ''}
                </div>
            </div>
            <div class="card-body">
                <p class="card-text">${notification.message}</p>
                ${relatedContent ? `<div class="mt-2">${relatedContent}</div>` : ''}
            </div>
        `;
        
        notificationsList.appendChild(notificationCard);
    });
    
    // Initialize Feather icons
    feather.replace();
    
    // Add event listeners to mark read buttons
    document.querySelectorAll('.mark-read-btn').forEach(button => {
        button.addEventListener('click', function() {
            const notificationId = this.dataset.id;
            markAsRead([notificationId]);
        });
    });
}

// Mark notifications as read
function markAsRead(notificationIds) {
    fetch('/notifications/mark-read', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ notification_ids: notificationIds })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Update UI to show notifications as read
            notificationIds.forEach(id => {
                const card = document.querySelector(`.card[data-notification-id="${id}"]`);
                if (card) {
                    card.classList.remove('border-primary');
                    card.classList.add('opacity-75');
                    
                    const markReadBtn = card.querySelector('.mark-read-btn');
                    if (markReadBtn) {
                        markReadBtn.remove();
                    }
                }
            });
            
            // Update unread count
            const unreadBadge = document.querySelector('.notification-badge');
            if (unreadBadge) {
                if (data.unread_count > 0) {
                    unreadBadge.textContent = data.unread_count > 99 ? '99+' : data.unread_count;
                    unreadBadge.classList.remove('d-none');
                } else {
                    unreadBadge.classList.add('d-none');
                }
            }
            
            // Update local data
            notificationsData = notificationsData.map(notification => {
                if (notificationIds.includes(notification.id)) {
                    notification.read = true;
                }
                return notification;
            });
        }
    })
    .catch(error => console.error('Error marking notifications as read:', error));
}

// Mark all notifications as read
function markAllAsRead() {
    const confirmDialog = confirm('Are you sure you want to mark all notifications as read?');
    if (!confirmDialog) return;
    
    fetch('/notifications/mark-all-read', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('All notifications marked as read.', 'success');
            
            // Reload notifications to reflect changes
            loadNotifications(currentPage);
        }
    })
    .catch(error => {
        console.error('Error marking all notifications as read:', error);
        showAlert('Failed to mark notifications as read.', 'danger');
    });
}

// Toggle filter for unread notifications
function toggleUnreadFilter() {
    const checkbox = document.getElementById('unread-filter');
    if (checkbox) {
        unreadOnly = checkbox.checked;
        
        // Reset to first page when filter changes
        loadNotifications(1);
    }
}

// Load previous page of notifications
function loadPreviousPage(e) {
    e.preventDefault();
    if (currentPage > 1) {
        loadNotifications(currentPage - 1);
    }
}

// Load next page of notifications
function loadNextPage(e) {
    e.preventDefault();
    if (currentPage < totalPages) {
        loadNotifications(currentPage + 1);
    }
}

// Update pagination UI
function updatePagination(currentPage, totalPages) {
    const pagination = document.getElementById('notifications-pagination');
    if (!pagination) return;
    
    // Update pagination text
    const paginationText = document.getElementById('notifications-pagination-text');
    if (paginationText) {
        paginationText.textContent = `Page ${currentPage} of ${totalPages}`;
    }
    
    // Update previous button
    const prevButton = document.getElementById('notifications-previous');
    if (prevButton) {
        if (currentPage <= 1) {
            prevButton.classList.add('disabled');
        } else {
            prevButton.classList.remove('disabled');
        }
    }
    
    // Update next button
    const nextButton = document.getElementById('notifications-next');
    if (nextButton) {
        if (currentPage >= totalPages) {
            nextButton.classList.add('disabled');
        } else {
            nextButton.classList.remove('disabled');
        }
    }
    
    // Show/hide pagination based on total pages
    if (totalPages <= 1) {
        pagination.classList.add('d-none');
    } else {
        pagination.classList.remove('d-none');
    }
}

// Show alert message
function showAlert(message, type = 'info') {
    const alertContainer = document.getElementById('notifications-alerts');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alert.classList.remove('show');
        setTimeout(() => alert.remove(), 150);
    }, 5000);
}

// Create a new notification (for testing)
function createTestNotification(message, type = 'info', loadId = null, driverId = null) {
    const data = {
        message: message,
        type: type,
        load_id: loadId,
        driver_id: driverId,
        send: true
    };
    
    fetch('/notifications/create', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showAlert('Test notification created successfully.', 'success');
            
            // Reload notifications to include the new one
            loadNotifications(1);
        } else {
            showAlert(`Failed to create notification: ${data.error}`, 'danger');
        }
    })
    .catch(error => {
        console.error('Error creating notification:', error);
        showAlert('Failed to create notification.', 'danger');
    });
}
