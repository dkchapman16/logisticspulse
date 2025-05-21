// Animations and gamification effects

// Global variables for confetti
let confettiCanvas;
let confettiContext;
let confettiAnimationId;
let confettiParticles = [];

// Initialize confetti canvas
function initConfetti() {
    // Create canvas if it doesn't exist
    if (!confettiCanvas) {
        confettiCanvas = document.createElement('canvas');
        confettiCanvas.id = 'confetti-canvas';
        confettiCanvas.style.position = 'fixed';
        confettiCanvas.style.top = '0';
        confettiCanvas.style.left = '0';
        confettiCanvas.style.width = '100%';
        confettiCanvas.style.height = '100%';
        confettiCanvas.style.pointerEvents = 'none';
        confettiCanvas.style.zIndex = '9999';
        document.body.appendChild(confettiCanvas);
        
        // Set canvas size
        resizeConfetti();
        
        // Add resize listener
        window.addEventListener('resize', resizeConfetti);
        
        // Get context
        confettiContext = confettiCanvas.getContext('2d');
    }
}

// Resize confetti canvas
function resizeConfetti() {
    if (confettiCanvas) {
        confettiCanvas.width = window.innerWidth;
        confettiCanvas.height = window.innerHeight;
    }
}

// Show confetti animation
function showConfetti() {
    // Initialize confetti canvas
    initConfetti();
    
    // Clear any existing animation
    if (confettiAnimationId) {
        cancelAnimationFrame(confettiAnimationId);
        confettiParticles = [];
    }
    
    // Create confetti particles
    createConfettiParticles();
    
    // Start animation
    animateConfetti();
    
    // Remove canvas after animation completes
    setTimeout(() => {
        if (confettiAnimationId) {
            cancelAnimationFrame(confettiAnimationId);
            confettiAnimationId = null;
        }
        confettiParticles = [];
        if (confettiCanvas) {
            confettiContext.clearRect(0, 0, confettiCanvas.width, confettiCanvas.height);
        }
    }, 5000);
}

// Create confetti particles
function createConfettiParticles() {
    const particleCount = 150;
    // Use FreightPace brand colors from the creative vision
    const colors = [
        '#00C48C', // Mint Green (Primary Action) 
        '#FFD700', // Celebration Gold
        '#1E1F25', // Graphite Black (Secondary Accent)
        '#FFFFFF', // White
        '#FF5757'  // Punch Red (Highlight Alert)
    ];
    
    for (let i = 0; i < particleCount; i++) {
        confettiParticles.push({
            x: Math.random() * confettiCanvas.width,
            y: Math.random() * -confettiCanvas.height,
            color: colors[Math.floor(Math.random() * colors.length)],
            size: Math.random() * 10 + 5,
            speed: Math.random() * 5 + 2,
            angle: Math.random() * 360,
            rotation: Math.random() * 360,
            rotationSpeed: Math.random() * 2 - 1
        });
    }
}

// Animate confetti particles
function animateConfetti() {
    // Clear canvas
    confettiContext.clearRect(0, 0, confettiCanvas.width, confettiCanvas.height);
    
    // Update and draw particles
    for (let i = 0; i < confettiParticles.length; i++) {
        const particle = confettiParticles[i];
        
        // Update position
        particle.y += particle.speed;
        particle.x += Math.sin(particle.angle * Math.PI / 180) * 2;
        
        // Update rotation
        particle.rotation += particle.rotationSpeed;
        
        // Draw particle
        confettiContext.save();
        confettiContext.translate(particle.x, particle.y);
        confettiContext.rotate(particle.rotation * Math.PI / 180);
        confettiContext.fillStyle = particle.color;
        confettiContext.fillRect(-particle.size / 2, -particle.size / 2, particle.size, particle.size);
        confettiContext.restore();
        
        // Remove particles that have fallen out of view
        if (particle.y > confettiCanvas.height) {
            confettiParticles.splice(i, 1);
            i--;
        }
    }
    
    // Continue animation
    if (confettiParticles.length > 0) {
        confettiAnimationId = requestAnimationFrame(animateConfetti);
    } else {
        confettiAnimationId = null;
    }
}

// Slot machine effect for achievement unlocks
function showSlotMachineEffect(container, finalValue, prefix = '', suffix = '') {
    if (!container) return;
    
    // Get original text
    const originalText = container.textContent;
    
    // Extract number from final value
    const finalNumber = parseInt(finalValue);
    if (isNaN(finalNumber)) return;
    
    // Animation variables
    let currentValue = 0;
    const duration = 2000; // milliseconds
    const startTime = Date.now();
    const endTime = startTime + duration;
    
    // Create animation
    function updateValue() {
        const now = Date.now();
        const progress = Math.min(1, (now - startTime) / duration);
        
        // Easing function for natural slowdown
        const easedProgress = 1 - Math.pow(1 - progress, 3);
        
        // Calculate current value with some randomness for slot machine effect
        if (progress < 1) {
            currentValue = Math.floor(easedProgress * finalNumber);
            
            // Add some randomness to simulate slot machine
            if (progress < 0.8) {
                currentValue += Math.floor(Math.random() * 10) - 5;
                currentValue = Math.max(0, currentValue);
            }
            
            container.textContent = prefix + currentValue + suffix;
            requestAnimationFrame(updateValue);
        } else {
            // Final value
            container.textContent = prefix + finalNumber + suffix;
        }
    }
    
    // Start animation
    updateValue();
    
    // Play slot machine sound
    playSlotMachineSound();
}

// Play slot machine sound effect
function playSlotMachineSound() {
    const audio = new Audio();
    audio.src = 'https://freesound.org/data/previews/337/337049_3232293-lq.mp3'; // Slot machine sound
    audio.volume = 0.5;
    audio.play().catch(error => {
        console.log('Audio playback prevented by browser: ' + error);
    });
}

// Play success sound effect
function playSuccessSound() {
    const audio = new Audio();
    audio.src = 'https://freesound.org/data/previews/320/320654_5260872-lq.mp3'; // Success chime
    audio.volume = 0.5;
    audio.play().catch(error => {
        console.log('Audio playback prevented by browser: ' + error);
    });
}

// Play coin sound effect for achievements
function playCoinSound() {
    const audio = new Audio();
    audio.src = 'https://freesound.org/data/previews/511/511484_9353313-lq.mp3'; // Coin sound
    audio.volume = 0.5;
    audio.play().catch(error => {
        console.log('Audio playback prevented by browser: ' + error);
    });
}

// Pulse animation for important elements
function pulseElement(element) {
    if (!element) return;
    
    // Add pulse class
    element.classList.add('pulse-animation');
    
    // Remove class after animation completes
    setTimeout(() => {
        element.classList.remove('pulse-animation');
    }, 1000);
}

// Show celebration for milestone achievements
function celebrateMilestone(milestoneType, value, driverName) {
    // Create milestone popup
    const milestonePopup = document.createElement('div');
    milestonePopup.className = 'milestone-popup';
    
    let milestoneTitle = 'Achievement Unlocked!';
    let milestoneDescription = '';
    
    // Set appropriate message based on milestone type
    switch (milestoneType) {
        case 'consecutive_on_time':
            milestoneTitle = 'On-Time Streak!';
            milestoneDescription = `${driverName} has achieved ${value} consecutive on-time deliveries!`;
            break;
        case 'monthly_perfect':
            milestoneTitle = 'Perfect Month!';
            milestoneDescription = `${driverName} has achieved a perfect on-time month!`;
            break;
        case 'total_loads':
            milestoneTitle = 'Load Milestone!';
            milestoneDescription = `${driverName} has completed ${value} total loads!`;
            break;
        default:
            milestoneDescription = `${driverName} has achieved a new milestone: ${value}!`;
    }
    
    milestonePopup.innerHTML = `
        <div class="milestone-content">
            <h3>${milestoneTitle}</h3>
            <p>${milestoneDescription}</p>
            <button class="btn btn-primary">Celebrate!</button>
        </div>
    `;
    
    // Add to document
    document.body.appendChild(milestonePopup);
    
    // Add event listener to button
    const celebrateBtn = milestonePopup.querySelector('button');
    celebrateBtn.addEventListener('click', () => {
        showConfetti();
        milestonePopup.classList.add('milestone-closing');
        setTimeout(() => {
            milestonePopup.remove();
        }, 500);
    });
    
    // Show the popup
    setTimeout(() => {
        milestonePopup.classList.add('milestone-visible');
    }, 100);
    
    // Auto-close after 7 seconds if not closed manually
    setTimeout(() => {
        if (document.body.contains(milestonePopup)) {
            milestonePopup.classList.add('milestone-closing');
            setTimeout(() => {
                if (document.body.contains(milestonePopup)) {
                    milestonePopup.remove();
                }
            }, 500);
        }
    }, 7000);
}

// Document ready initialization
document.addEventListener('DOMContentLoaded', function() {
    // Initialize animations as needed
});
