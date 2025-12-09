// Santa's Gift Workshop - Interactive Frontend
// Handles SignalWire connection and dynamic gift display

// Token and address will be fetched dynamically from /get_token
let currentToken = null;
let currentDestination = null;

let client;
let roomSession;
let isMuted = false;

// Audio settings (default all off)
let audioSettings = {
    echoCancellation: true,
    noiseSuppression: false,
    autoGainControl: false
};

// Gift state
let giftState = {
    searchQuery: '',
    gifts: [],
    selectedGift: null,
    status: 'waiting'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeUI();
    initializeSettings();
    createChristmasLights();
    startSnowfall();
    updateChristmasCountdown();
    setInterval(updateChristmasCountdown, 1000);

    // Recreate lights on window resize for responsive layout
    window.addEventListener('resize', () => {
        createChristmasLights();
    });
});

// Initialize UI elements
function initializeUI() {
    const startBtn = document.getElementById('startBtn');
    const endBtn = document.getElementById('endBtn');
    const muteBtn = document.getElementById('muteBtn');

    startBtn.addEventListener('click', startCall);
    endBtn.addEventListener('click', endCall);
    muteBtn.addEventListener('click', toggleMute);
}

// Initialize audio settings
function initializeSettings() {
    // Load saved settings from localStorage
    const saved = localStorage.getItem('santaAudioSettings');
    if (saved) {
        audioSettings = JSON.parse(saved);
    }

    // Update checkboxes
    document.getElementById('echoCancellation').checked = audioSettings.echoCancellation;
    document.getElementById('noiseSuppression').checked = audioSettings.noiseSuppression;
    document.getElementById('autoGainControl').checked = audioSettings.autoGainControl;

    // Settings toggle button
    const settingsToggle = document.getElementById('settingsToggle');
    const settingsPanel = document.getElementById('settingsPanel');
    const settingsClose = document.getElementById('settingsClose');

    settingsToggle.addEventListener('click', () => {
        settingsPanel.classList.toggle('show');
    });

    settingsClose.addEventListener('click', () => {
        settingsPanel.classList.remove('show');
    });

    // Handle checkbox changes
    document.getElementById('echoCancellation').addEventListener('change', (e) => {
        audioSettings.echoCancellation = e.target.checked;
        saveSettings();
    });

    document.getElementById('noiseSuppression').addEventListener('change', (e) => {
        audioSettings.noiseSuppression = e.target.checked;
        saveSettings();
    });

    document.getElementById('autoGainControl').addEventListener('change', (e) => {
        audioSettings.autoGainControl = e.target.checked;
        saveSettings();
    });
}

// Save settings to localStorage
function saveSettings() {
    localStorage.setItem('santaAudioSettings', JSON.stringify(audioSettings));
    updateSantaMessage('Audio settings updated! Apply on next call.');
}

// Start call to Santa
async function startCall() {
    // Debounce - disable button immediately to prevent double-clicks
    const startBtn = document.getElementById('startBtn');
    if (startBtn.disabled) {
        console.log('Call already in progress');
        return;
    }
    startBtn.disabled = true;
    startBtn.textContent = '🎅 Connecting...';

    try {
        updateStatus('connecting', '🎅 Getting token...');

        // Fetch token and address dynamically from the server
        const tokenResp = await fetch('/get_token');
        const tokenData = await tokenResp.json();

        if (tokenData.error) {
            throw new Error(tokenData.error);
        }

        currentToken = tokenData.token;
        currentDestination = tokenData.address;

        console.log('Got token, destination:', currentDestination);
        updateStatus('connecting', '🎅 Connecting to Santa...');

        // Initialize SignalWire client with dynamic token
        client = await SignalWire.SignalWire({
            token: currentToken
        });

        // Subscribe to user events at client level
        client.on('user_event', (params) => {
            console.log('🎅 CLIENT EVENT: user_event', params);
            handleUserEvent(params);
        });

        // Get video container for SignalWire to inject video
        const videoContainer = document.getElementById('video-container');

        // Dial the call with proper parameters (following holyguacamole pattern)
        roomSession = await client.dial({
            to: currentDestination,
            rootElement: videoContainer,  // SignalWire will inject video here
            audio: {
                echoCancellation: audioSettings.echoCancellation,
                noiseSuppression: audioSettings.noiseSuppression,
                autoGainControl: audioSettings.autoGainControl
            },
            video: true,
            negotiateVideo: true,  // Important for video negotiation with AI agent
            userVariables: {
                userName: 'Santa Workshop Guest',
                interface: 'web-ui',
                timestamp: new Date().toISOString()
            }
        });

        console.log('Room session created:', roomSession);

        // Subscribe to room session events
        roomSession.on('call.joined', async (params) => {
            console.log('Call joined:', params);

            // Hide the placeholder when connected
            const placeholder = document.getElementById('video-placeholder');
            if (placeholder) {
                placeholder.style.display = 'none';
            }

            handleRoomJoined(params);
        });

        roomSession.on('call.updated', async (params) => {
            console.log('Call updated:', params);
            handleRoomUpdated(params);
        });

        roomSession.on('call.ended', async (params) => {
            console.log('Call ended:', params);
            handleRoomEnded(params);
            disconnect();
        });

        // Handle various disconnect events
        roomSession.on('destroy', (params) => {
            console.log('Session destroyed:', params);
            disconnect();
        });

        roomSession.on('room.left', (params) => {
            console.log('Room left:', params);
            disconnect();
        });

        // Handle video stream events
        roomSession.on('stream.started', async (params) => {
            console.log('Stream started:', params);
        });

        roomSession.on('media.connected', async (params) => {
            console.log('Media connected:', params);
        });

        // Handle user events on room session too
        roomSession.on('user_event', (params) => {
            console.log('🎅 ROOM EVENT: user_event', params);
            console.log('Event params structure:', JSON.stringify(params, null, 2));
            handleUserEvent(params);
        });

        // START THE CALL - Critical!
        await roomSession.start();
        console.log('Call started successfully');

        // Update UI
        document.getElementById('startBtn').style.display = 'none';
        document.getElementById('endBtn').style.display = 'block';
        document.getElementById('muteBtn').style.display = 'block';

        updateStatus('connected', '🎄 Talking with Santa!');

    } catch (error) {
        console.error('Failed to connect to Santa:', error);
        updateStatus('error', '❌ Could not reach Santa');

        // Re-enable the start button on error
        const startBtn = document.getElementById('startBtn');
        startBtn.disabled = false;
        startBtn.innerHTML = '<span class="btn-icon">🎤</span><span class="btn-text">Talk to Santa!</span>';
    }
}

// Handle room joined
function handleRoomJoined(params) {
    console.log('Connected to Santa\'s Workshop!', params);
    updateSantaMessage('Ho ho ho! Hello there! What\'s your name?');
}

// Handle room updates
function handleRoomUpdated(params) {
    console.log('Room updated:', params);
}

// Handle room ended
function handleRoomEnded(params) {
    console.log('Call with Santa ended', params);
    resetUI();
}

// End call button handler - properly hangup first
async function endCall() {
    console.log('End call button clicked');
    await hangup();
}

// Hangup function (following holyguacamole pattern)
async function hangup() {
    try {
        if (roomSession) {
            console.log('Hanging up call...');
            await roomSession.hangup();
            console.log('Call hung up successfully');
        }
    } catch (error) {
        console.error('Hangup error:', error);
        // Continue with disconnect even if hangup fails
    }

    // Always disconnect to clean up
    disconnect();
}

// Disconnect and cleanup (following holyguacamole pattern)
function disconnect() {
    console.log('Disconnect called - cleaning up...');

    // Clean up local stream if it exists
    if (roomSession && roomSession.localStream) {
        console.log('Stopping local stream tracks');
        roomSession.localStream.getTracks().forEach(track => {
            track.stop();
        });
    }

    // Clean up room session
    roomSession = null;

    // Disconnect the client properly
    if (client) {
        try {
            console.log('Disconnecting client');
            client.disconnect();
        } catch (e) {
            console.log('Client disconnect error:', e);
        }
        client = null;
    }

    // Clean up video container
    const videoContainer = document.getElementById('video-container');
    if (videoContainer) {
        console.log('Cleaning video container');

        // Stop any video streams in the container
        const videos = videoContainer.querySelectorAll('video');
        videos.forEach(video => {
            if (video.srcObject) {
                video.srcObject.getTracks().forEach(track => track.stop());
                video.srcObject = null;
            }
        });

        // Clear and restore placeholder
        videoContainer.innerHTML = '';
        const placeholder = document.createElement('div');
        placeholder.id = 'video-placeholder';
        placeholder.innerHTML = `
            <div class="santa-placeholder">
                <div class="santa-emoji-large">🎅</div>
                <h3>Santa's Workshop</h3>
                <p>Click "Talk to Santa!" to begin your magical journey</p>
                <div class="christmas-icons">
                    <span>🎄</span>
                    <span>🎁</span>
                    <span>⛷️</span>
                    <span>🎿</span>
                    <span>🎄</span>
                </div>
            </div>
        `;
        videoContainer.appendChild(placeholder);
    }

    resetUI();
}

// Toggle mute - using the holyguacamole method that actually works
function toggleMute() {
    if (!roomSession) return;

    isMuted = !isMuted;

    // Mute/unmute by controlling the audio tracks directly
    try {
        if (roomSession.localStream) {
            // Mute/unmute the audio track
            const audioTracks = roomSession.localStream.getAudioTracks();
            audioTracks.forEach(track => {
                track.enabled = !isMuted;
            });
        } else if (roomSession.peer && roomSession.peer.localStream) {
            // Try alternate method
            const audioTracks = roomSession.peer.localStream.getAudioTracks();
            audioTracks.forEach(track => {
                track.enabled = !isMuted;
            });
        } else {
            console.warn('Unable to find local stream to mute/unmute');
        }
    } catch (e) {
        console.error('Error toggling mute:', e);
    }

    // Update button text
    document.getElementById('muteBtn').innerHTML = isMuted ?
        '<span class="btn-icon">🔊</span><span class="btn-text">Unmute</span>' :
        '<span class="btn-icon">🔇</span><span class="btn-text">Mute</span>';

    // Show status message
    updateSantaMessage(isMuted ? 'Microphone muted' : 'Microphone unmuted');
}

// Handle user events from backend
function handleUserEvent(params) {
    console.log('User event received:', params);

    // Match holyguacamole's event structure handling
    let eventData = params;
    if (params && params.event) {
        eventData = params.event;
    }

    if (!eventData || !eventData.type) {
        console.log('No valid event data found');
        return;
    }

    const eventType = eventData.type;  // Changed from event_type to type

    // Comprehensive debug logging
    console.log('\n=== FRONTEND EVENT RECEIVED ===');
    console.log(`Event Type: ${eventType}`);
    console.log('Event Data:', JSON.stringify(eventData, null, 2));
    console.log('=== END EVENT DATA ===\n');

    // Add to event log if visible
    logEvent(eventType, eventData);

    // Get elements once for all cases
    const showcase = document.getElementById('giftShowcase');
    const gallery = document.getElementById('giftGallery');

    switch (eventType) {
        case 'gifts_found':
            console.log('DEBUG Frontend: Received gifts_found event');
            console.log('DEBUG Frontend: Gift data:', eventData.gifts);

            // Reset the display: hide showcase, show gallery
            showcase.style.display = 'none';
            gallery.style.display = 'grid';

            // Display the new gifts
            displayGifts(eventData.gifts);
            showSearchStatus(false);
            updateStatus('selecting', '🎁 Choose your gift!');
            break;

        case 'gift_selected':
            displaySelectedGift(eventData.gift);
            playSound('jingleBells');
            showConfetti();
            updateStatus('confirmed', '✨ Gift Selected!');
            break;

        case 'nice_list_checked':
            displayNiceListResult(eventData.name, eventData.status);
            break;

        case 'search_failed':
            console.log('DEBUG Frontend: Search failed event received');
            showSearchStatus(false);
            updateStatus('error', '🎄 Let me check my workshop again...');
            // Clear the gallery and show a message
            gallery.innerHTML = `
                <div class="welcome-state">
                    <h3>Oh dear!</h3>
                    <p>Santa's workshop catalog is being updated by the elves!</p>
                    <p>Please tell me more about what you'd like!</p>
                    <div class="christmas-icons">
                        <span>🎁</span><span>🔧</span><span>🎄</span>
                    </div>
                </div>
            `;
            break;

        case 'searching':
            // Reset display when starting a new search
            showcase.style.display = 'none';
            gallery.style.display = 'grid';
            gallery.innerHTML = ''; // Clear previous results

            showSearchStatus(true);
            updateStatus('searching', '🔍 Santa is looking...');
            break;

        default:
            console.log('Unknown event type:', eventType);
    }
}

// Display gifts from search
function displayGifts(gifts) {
    console.log(`DEBUG Frontend: displayGifts called with ${gifts ? gifts.length : 0} gifts`);

    const gallery = document.getElementById('giftGallery');
    const welcomeState = document.getElementById('welcomeState');

    if (!gifts || gifts.length === 0) {
        console.log('DEBUG Frontend: No gifts to display');
        return;
    }

    // Hide welcome state
    if (welcomeState) {
        welcomeState.style.display = 'none';
    }

    // Clear gallery
    gallery.innerHTML = '';

    // Display each gift as a card
    console.log(`DEBUG Frontend: Processing ${gifts.length} gifts for display`);
    gifts.forEach((gift, index) => {
        console.log(`DEBUG Frontend: Creating card for gift ${index + 1}/${gifts.length}: ${gift.title}`);
        const card = createGiftCard(gift, index + 1);
        gallery.appendChild(card);

        // Stagger animation
        setTimeout(() => {
            card.style.animation = 'slideIn 0.5s ease-out';
        }, index * 100);
    });

    console.log(`DEBUG Frontend: Finished appending ${gallery.children.length} gift cards to gallery`);
}

// Create gift card element
function createGiftCard(gift, optionNumber) {
    const card = document.createElement('div');
    card.className = 'gift-card';
    card.onclick = () => selectGift(optionNumber);

    // Image
    const img = document.createElement('img');
    img.className = 'gift-card-image';
    img.src = gift.image || 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"><rect width="300" height="200" fill="%23f0f0f0"/><text x="50%" y="50%" text-anchor="middle" alignment-baseline="middle" font-size="60">🎁</text></svg>';
    img.alt = gift.title;
    img.onerror = () => {
        img.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200"><rect width="300" height="200" fill="%23f0f0f0"/><text x="50%" y="50%" text-anchor="middle" alignment-baseline="middle" font-size="60">🎁</text></svg>';
    };

    // Body
    const body = document.createElement('div');
    body.className = 'gift-card-body';

    // Option number
    const optionBadge = document.createElement('div');
    optionBadge.className = 'gift-option-number';
    optionBadge.textContent = optionNumber;

    // Title
    const title = document.createElement('h3');
    title.className = 'gift-card-title';
    title.textContent = gift.title || 'Mystery Gift';

    // Price
    const price = document.createElement('div');
    price.className = 'gift-card-price';
    price.textContent = gift.price || 'Ask Santa!';

    // Description
    const desc = document.createElement('p');
    desc.className = 'gift-card-description';
    desc.textContent = gift.description || 'A wonderful Christmas gift!';

    // Ribbon
    const ribbon = document.createElement('div');
    ribbon.className = 'gift-card-ribbon';
    ribbon.textContent = 'New!';

    body.appendChild(optionBadge);
    body.appendChild(title);
    body.appendChild(price);
    body.appendChild(desc);

    card.appendChild(img);
    card.appendChild(body);
    card.appendChild(ribbon);

    return card;
}

// Select a gift
function selectGift(optionNumber) {
    console.log('Selecting gift option:', optionNumber);
    // The actual selection will be handled by voice command
    // This is just visual feedback
    const cards = document.querySelectorAll('.gift-card');
    cards.forEach((card, index) => {
        if (index === optionNumber - 1) {
            card.style.transform = 'scale(1.1)';
            card.style.boxShadow = '0 10px 40px rgba(255, 215, 0, 0.5)';
        } else {
            card.style.opacity = '0.5';
        }
    });
}

// Display selected gift showcase
function displaySelectedGift(gift) {
    const showcase = document.getElementById('giftShowcase');
    const gallery = document.getElementById('giftGallery');

    // Hide gallery
    gallery.style.display = 'none';

    // Update showcase
    document.getElementById('showcaseImage').src = gift.image || 'placeholder.jpg';
    document.getElementById('showcaseName').textContent = gift.title;
    document.getElementById('showcasePrice').textContent = gift.price;

    // Show showcase
    showcase.style.display = 'block';
}

// Display nice list result
function displayNiceListResult(name, status) {
    const checker = document.getElementById('niceListChecker');
    const result = document.getElementById('listResult');

    result.innerHTML = `
        <div class="nice-badge">✨</div>
        <p>${name} is on the <strong>NICE LIST!</strong></p>
        <p>Keep being wonderful!</p>
    `;

    checker.style.display = 'block';

    setTimeout(() => {
        checker.style.display = 'none';
    }, 5000);
}

// Update Santa's message bubble - removed to declutter UI
function updateSantaMessage(message) {
    // Message bubble removed for cleaner interface
    console.log('Santa says:', message);
}


// Show/hide search status
function showSearchStatus(show) {
    const searchStatus = document.getElementById('searchStatus');
    searchStatus.style.display = show ? 'block' : 'none';
}

// Update status display (removed from UI)
function updateStatus(state, text) {
    // Status display has been removed from the UI
    // Keeping function as no-op to avoid breaking existing calls
    console.log(`Status: ${state} - ${text}`);
}

// Reset UI to initial state
function resetUI() {
    const startBtn = document.getElementById('startBtn');
    startBtn.style.display = 'block';
    startBtn.disabled = false;
    startBtn.innerHTML = '<span class="btn-icon">🎤</span><span class="btn-text">Talk to Santa!</span>';

    document.getElementById('endBtn').style.display = 'none';
    document.getElementById('muteBtn').style.display = 'none';

    document.getElementById('giftGallery').innerHTML = `
        <div class="welcome-state" id="welcomeState">
            <div class="workshop-scene">
                <div class="elf elf-1">🧝</div>
                <div class="elf elf-2">🧝‍♀️</div>
                <div class="gift-box gift-1">🎁</div>
                <div class="gift-box gift-2">🎄</div>
                <div class="gift-box gift-3">🎀</div>
            </div>
            <h3>Santa's Workshop</h3>
            <p>Tell Santa what you'd like for Christmas!</p>
        </div>
    `;

    document.getElementById('giftShowcase').style.display = 'none';
    document.getElementById('searchStatus').style.display = 'none';

    updateStatus('waiting', 'Ready to Chat');
    updateSantaMessage('Ho ho ho! Click below to talk to me!');
}

// Create twinkling Christmas lights
function createChristmasLights() {
    const lightsContainer = document.querySelector('.christmas-lights');
    if (!lightsContainer) return;

    const colors = ['red', 'green', 'yellow', 'blue', 'purple', 'orange'];
    const numberOfLights = Math.floor(window.innerWidth / 25); // One light every 25px

    // Clear existing lights
    lightsContainer.innerHTML = '';

    // Create the wire first
    const wire = document.createElement('div');
    wire.style.position = 'absolute';
    wire.style.top = '10px';
    wire.style.left = '0';
    wire.style.right = '0';
    wire.style.height = '2px';
    wire.style.background = '#333';
    wire.style.zIndex = '-1';
    lightsContainer.appendChild(wire);

    // Create individual light bulbs
    for (let i = 0; i < numberOfLights; i++) {
        const light = document.createElement('div');
        light.className = `light-bulb light-${colors[i % colors.length]}`;

        // Randomize animation delay for more natural twinkling
        const randomDelay = Math.random() * 2;
        light.style.animationDelay = `${randomDelay}s`;

        // Vary animation duration slightly for each light
        const randomDuration = 1.5 + Math.random() * 1.5;
        light.style.animationDuration = `${randomDuration}s`;

        lightsContainer.appendChild(light);
    }
}

// Start snowfall animation with accumulation
function startSnowfall() {
    const container = document.getElementById('snowContainer');
    const snowflakes = ['❄', '❅', '❆', '✻', '✼', '❄'];

    // Create snow accumulation layer at bottom
    const snowLayer = document.createElement('div');
    snowLayer.className = 'snow-accumulation';
    snowLayer.id = 'snowAccumulation';
    document.body.appendChild(snowLayer);

    let accumulatedHeight = 0;
    const maxHeight = 200; // Maximum accumulation in pixels

    // Create more snow (reduced interval from 300ms to 100ms)
    setInterval(() => {
        // Create 2-3 snowflakes at once for denser snow
        const flakeCount = Math.floor(Math.random() * 2) + 2;

        for (let i = 0; i < flakeCount; i++) {
            const flake = document.createElement('div');
            flake.className = 'snowflake';
            flake.textContent = snowflakes[Math.floor(Math.random() * snowflakes.length)];
            flake.style.left = Math.random() * 100 + '%';
            flake.style.animationDuration = Math.random() * 3 + 4 + 's';
            flake.style.fontSize = Math.random() * 15 + 8 + 'px';

            container.appendChild(flake);

            // Remove flake after animation and add to accumulation
            setTimeout(() => {
                flake.remove();
                // Gradually increase snow accumulation
                if (accumulatedHeight < maxHeight) {
                    accumulatedHeight += 0.15;
                    snowLayer.style.height = accumulatedHeight + 'px';
                }
            }, 7000);
        }
    }, 100); // More frequent snow generation
}

// Update Christmas countdown
function updateChristmasCountdown() {
    const countdown = document.getElementById('christmasCountdown');
    const christmas = new Date(new Date().getFullYear(), 11, 25);
    const now = new Date();

    if (now.getMonth() === 11 && now.getDate() > 25) {
        christmas.setFullYear(christmas.getFullYear() + 1);
    }

    const diff = christmas - now;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
        countdown.textContent = '🎄 It\'s Christmas Day! 🎅';
    } else if (days === 1) {
        countdown.textContent = '🎄 1 day until Christmas! 🎅';
    } else {
        countdown.textContent = `🎄 ${days} days until Christmas! 🎅`;
    }
}

// Magic meter function removed - UI simplified

// Show confetti animation
function showConfetti() {
    const confettiContainer = document.getElementById('confetti');
    const colors = ['#ff0000', '#00ff00', '#0000ff', '#ffff00', '#ff00ff'];

    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const piece = document.createElement('div');
            piece.className = 'confetti-piece';
            piece.style.left = Math.random() * 100 + '%';
            piece.style.background = colors[Math.floor(Math.random() * colors.length)];
            piece.style.animationDelay = Math.random() * 0.5 + 's';

            confettiContainer.appendChild(piece);

            setTimeout(() => {
                piece.remove();
            }, 3000);
        }, i * 30);
    }
}

// Play sound effect
function playSound(soundId) {
    const audio = document.getElementById(soundId);
    if (audio) {
        audio.play().catch(e => console.log('Could not play sound:', e));
    }
}

// Log events for debugging
function logEvent(type, data) {
    const logContainer = document.getElementById('logContent');
    if (!logContainer || document.getElementById('eventLog').style.display === 'none') return;

    const entry = document.createElement('div');
    entry.className = 'log-entry';

    const timestamp = new Date().toLocaleTimeString();
    entry.innerHTML = `
        <span class="log-timestamp">${timestamp}</span>
        <strong>${type}</strong>: ${JSON.stringify(data).substring(0, 100)}...
    `;

    logContainer.insertBefore(entry, logContainer.firstChild);

    // Keep only last 20 entries
    while (logContainer.children.length > 20) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

// Toggle event log visibility (for debugging)
window.toggleEventLog = function() {
    const log = document.getElementById('eventLog');
    log.style.display = log.style.display === 'none' ? 'block' : 'none';
};

// Clean up on page unload (following holyguacamole pattern)
window.addEventListener('beforeunload', () => {
    if (roomSession) {
        hangup();
    }
});
